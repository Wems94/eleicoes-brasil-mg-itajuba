import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from eleicoes import snapshots
from eleicoes.lgpd import verificar_snapshots
from eleicoes.snapshots import SCHEMA_VERSAO, eleicoes_removidas, gerar_snapshots

GERADO_EM = "2026-10-09T20:00:00+00:00"


@pytest.fixture
def con(banco_completo):
    c = duckdb.connect(str(banco_completo), read_only=True)
    yield c
    c.close()


@pytest.fixture
def publicado(con, tmp_path) -> Path:
    destino = tmp_path / "web" / "data"
    gerar_snapshots(con, destino, gerado_em=GERADO_EM)
    return destino


def _ler(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _arvore(d: Path) -> dict[str, bytes]:
    return {
        p.relative_to(d).as_posix(): p.read_bytes() for p in sorted(d.rglob("*")) if p.is_file()
    }


# --- estrutura e manifesto --------------------------------------------------------


def test_arquivos_gerados(publicado):
    arquivos = set(_arvore(publicado))
    assert {"manifest.json", "historico_itajuba.json"} <= arquivos
    for ano, turno in [(2018, 1), (2022, 1), (2022, 2)]:
        base = f"{ano}/{turno}"
        assert {
            f"{base}/brasil.json",
            f"{base}/itajuba.json",
            f"{base}/itajuba_secoes.json",
        } <= arquivos
        assert f"{base}/uf/MG.json" in arquivos
        assert f"{base}/uf/ZZ.json" in arquivos  # exterior (só Presidente)
    assert "2018/2/brasil.json" not in arquivos
    assert "geo/municipios.topo.json" in arquivos
    # camadas do mapa: todos os cargos no 1º turno; no 2º, só os que tiveram disputa
    cargos = ["presidente", "governador", "senador", "deputado-federal", "deputado-estadual"]
    assert {f"2022/1/mapa/{c}.json" for c in cargos} <= arquivos
    assert {a for a in arquivos if a.startswith("2022/2/mapa/")} == {
        "2022/2/mapa/presidente.json",
        "2022/2/mapa/governador.json",
    }
    # detalhe por UF e cargo; sem 2º turno de Governador em MG, sem arquivo
    assert "2022/1/municipios/MG/deputado-federal.json" in arquivos
    assert "2022/2/municipios/SP/governador.json" in arquivos
    assert "2022/2/municipios/MG/governador.json" not in arquivos
    assert not any(a.startswith("2022/1/municipios/ZZ/") for a in arquivos)


def test_manifesto(publicado):
    m = _ler(publicado / "manifest.json")
    assert m["schema_versao"] == SCHEMA_VERSAO
    assert m["gerado_em"] == GERADO_EM
    assert m["eleicoes"] == [{"ano": 2018, "turnos": [1]}, {"ano": 2022, "turnos": [1, 2]}]
    assert m["municipio"] == {"codigo": 46477, "nome": "ITAJUBÁ", "uf": "MG", "ibge": 3132404}
    assert "TSE" in m["fonte"]


def test_manifesto_traz_o_sha256_de_cada_origem(publicado, con):
    origens = _ler(publicado / "manifest.json")["origens"]
    esperado = con.execute("SELECT ano, turno, fonte, url, sha256 FROM staging.origens").fetchall()
    assert {(o["ano"], o["turno"], o["fonte"], o["url"], o["sha256"]) for o in origens} == set(
        esperado
    )
    assert all(len(o["sha256"]) == 64 for o in origens)


def test_manifesto_traz_o_sha256_de_cada_snapshot(publicado):
    m = _ler(publicado / "manifest.json")
    arquivos = {k: v for k, v in _arvore(publicado).items() if k != "manifest.json"}
    assert set(m["arquivos"]) == set(arquivos)
    for nome, corpo in arquivos.items():
        assert m["arquivos"][nome] == hashlib.sha256(corpo).hexdigest()


# --- conteúdo ---------------------------------------------------------------------------


def test_brasil(publicado, con):
    b = _ler(publicado / "2022" / "1" / "brasil.json")
    (validos,) = con.execute(
        "SELECT any_value(votos_validos) FROM marts.resultado_brasil WHERE ano=2022 AND turno=1"
    ).fetchone()
    p = b["presidente"]
    assert p["votos_validos"] == validos
    assert [c["numero"] for c in p["candidatos"]] == [13, 22, 15]  # ordenado por votos
    assert sum(c["votos"] for c in p["candidatos"]) == validos
    assert sum(c["pct"] for c in p["candidatos"]) == pytest.approx(100, abs=0.02)
    assert {u["uf"] for u in b["ufs"]} == {"MG", "SP", "ZZ"}
    mg = next(u for u in b["ufs"] if u["uf"] == "MG")
    assert set(mg["vencedor"]) == {"numero", "nome", "partido", "pct"}
    comp = b["comparecimento"]
    assert 0 < comp["pct_comparecimento"] < 100
    assert comp["pct_brancos"] == pytest.approx(
        100 * comp["brancos"] / comp["comparecimento"], abs=0.01
    )
    assert comp["pct_nulos"] == pytest.approx(
        100 * comp["nulos"] / comp["comparecimento"], abs=0.01
    )


def test_uf_tem_cargos_e_deputados_com_situacao(publicado):
    mg = _ler(publicado / "2022" / "1" / "uf" / "MG.json")
    assert [c["codigo"] for c in mg["cargos"]] == [1, 3, 5, 6, 7]
    dep = next(c for c in mg["cargos"] if c["codigo"] == 6)
    assert dep["nome"] == "Deputado Federal"
    assert [c["situacao"] for c in dep["candidatos"]] == [
        "ELEITO POR QP",
        "ELEITO POR MÉDIA",
        "SUPLENTE",
        "SUPLENTE",
    ]
    assert {c["codigo"] for c in mg["comparecimento"]} == {1, 3, 5, 6, 7}


def test_itajuba(publicado):
    it = _ler(publicado / "2022" / "1" / "itajuba.json")
    pres = next(c for c in it["cargos"] if c["codigo"] == 1)
    tipos = {v["tipo"] for v in pres["votaveis"]}
    assert tipos == {"candidato", "branco", "nulo"}
    assert pres["comparecimento"]["comparecimento"] > 0
    assert [z["zona"] for z in it["zonas"]] == [134]
    locais = {loc["local"]: loc for loc in it["locais"]}
    assert set(locais) == {1058, 1155}
    assert locais[1155]["lat"] == pytest.approx(-22.4267816)
    assert locais[1155]["secoes"] == [18, 19]


def test_busca_de_secao(publicado):
    s = _ler(publicado / "2022" / "1" / "itajuba_secoes.json")
    (sec,) = [x for x in s["secoes"] if (x["zona"], x["secao"]) == (134, 18)]
    assert sec["local"] == 1155
    comp = sec["comparecimento"]["3"]
    votos = sec["votos"]["3"]  # [[número, votos], ...]
    assert sum(q for _, q in votos) == comp["comparecimento"]
    assert set(s["votaveis"]["3"]) >= {str(n) for n, _ in votos if n not in (95, 96)}


def test_historico_de_itajuba(publicado):
    h = _ler(publicado / "historico_itajuba.json")
    assert {(p["ano"], p["turno"]) for p in h["partidos"]} == {(2018, 1), (2022, 1), (2022, 2)}
    assert {p["cargo"] for p in h["partidos"]} <= {1, 3, 5}  # só majoritários (spec)
    assert {(c["ano"], c["turno"]) for c in h["comparecimento"] if c["cargo"] == 1} == {
        (2018, 1),
        (2022, 1),
        (2022, 2),
    }


def test_snapshots_passam_no_verificador_lgpd(publicado):
    assert verificar_snapshots(publicado) == []


# --- atomicidade e determinismo -------------------------------------------------------------


def test_mesmos_dados_geram_os_mesmos_bytes(con, publicado, tmp_path):
    outro = tmp_path / "outro"
    gerar_snapshots(con, outro, gerado_em=GERADO_EM)
    assert _arvore(outro) == _arvore(publicado)


def test_nova_geracao_substitui_o_diretorio_inteiro(con, publicado):
    (publicado / "2010").mkdir()
    (publicado / "2010" / "velho.json").write_text("{}")

    gerar_snapshots(con, publicado, gerado_em=GERADO_EM)

    assert not (publicado / "2010").exists()
    assert (publicado / "manifest.json").exists()


def test_falha_no_meio_preserva_o_diretorio_publicado(con, publicado, monkeypatch):
    antes = _arvore(publicado)
    original = snapshots._itajuba

    def quebra(con_, ano, turno, *a, **k):
        if (ano, turno) == (2022, 2):
            raise RuntimeError("falha simulada")
        return original(con_, ano, turno, *a, **k)

    monkeypatch.setattr(snapshots, "_itajuba", quebra)
    with pytest.raises(RuntimeError, match="falha simulada"):
        gerar_snapshots(con, publicado, gerado_em="2030-01-01T00:00:00+00:00")

    assert _arvore(publicado) == antes
    assert sorted(p.name for p in publicado.parent.iterdir()) == ["data"]  # sem temporários


def test_gera_mesmo_sem_diretorio_anterior(con, tmp_path):
    destino = tmp_path / "a" / "b" / "data"
    gerar_snapshots(con, destino, gerado_em=GERADO_EM)
    assert (destino / "manifest.json").exists()


def test_validacao_roda_antes_da_troca(con, publicado):
    """O verificador LGPD olha o diretório temporário: um vazamento nunca chega
    a ser publicado, nem por um instante."""
    antes = _arvore(publicado)
    vistos = []

    def validar(tmp: Path) -> None:
        vistos.append(tmp)
        assert (tmp / "manifest.json").exists()
        raise RuntimeError("vazamento detectado")

    with pytest.raises(RuntimeError, match="vazamento"):
        gerar_snapshots(con, publicado, gerado_em="2030-01-01T00:00:00+00:00", validar=validar)

    assert vistos and vistos[0] != publicado
    assert _arvore(publicado) == antes


def _m(*eleicoes: tuple[int, list[int]]) -> dict:
    return {"eleicoes": [{"ano": a, "turnos": t} for a, t in eleicoes]}


def test_eleicoes_removidas_detecta_perda_de_publicacao():
    """Sem MotherDuck, o runner do CI começa vazio: rodar só 2026/1 apagaria 2018 e 2022
    do site. A trava do etl.yml usa esta função para impedir isso."""
    anterior = _m((2018, [1, 2]), (2022, [1, 2]))
    assert eleicoes_removidas(anterior, _m((2026, [1]))) == [
        (2018, 1),
        (2018, 2),
        (2022, 1),
        (2022, 2),
    ]
    assert eleicoes_removidas(anterior, _m((2018, [1, 2]), (2022, [1, 2]), (2026, [1]))) == []
    assert eleicoes_removidas(None, _m((2026, [1]))) == []  # primeira publicação


def test_cli_conferir_publicacao(tmp_path, capsys):
    a, n = tmp_path / "anterior.json", tmp_path / "novo.json"
    a.write_text(json.dumps(_m((2022, [1, 2]))))
    n.write_text(json.dumps(_m((2026, [1]))))
    assert snapshots.main(["conferir", str(a), str(n)]) == 1
    assert "2022/1" in capsys.readouterr().out
    n.write_text(json.dumps(_m((2022, [1, 2]), (2026, [1]))))
    assert snapshots.main(["conferir", str(a), str(n)]) == 0
    assert snapshots.main(["conferir", str(tmp_path / "nao_existe.json"), str(n)]) == 0


# --- mapa municipal (schema 2) ------------------------------------------------------------

ITAJUBA, BH, BRAZOPOLIS, SAO_PAULO = "3132404", "3106200", "3108909", "3550308"


def test_camada_de_presidente(publicado, con):
    m = _ler(publicado / "2022" / "1" / "mapa" / "presidente.json")
    assert (m["cargo"], m["nome"], m["por"]) == ("presidente", "Presidente", "candidato")
    assert set(m["municipios"]) == {BH, BRAZOPOLIS, ITAJUBA, SAO_PAULO}
    idx, pct, abst = m["municipios"][ITAJUBA]
    vencedor = m["votaveis"][idx]
    ((nome, pct_real, abst_real),) = con.execute(
        """SELECT r.nm_urna_candidato, r.pct_validos, c.pct_abstencao
           FROM marts.resultado_municipio r JOIN marts.comparecimento_municipio c
                USING (ano, turno, sg_uf, cd_municipio, cd_cargo)
           WHERE ano = 2022 AND turno = 1 AND cd_municipio = 46477 AND cd_cargo = 1
             AND posicao = 1"""
    ).fetchall()
    assert vencedor["nome"] == nome and vencedor["partido"]
    assert pct == round(pct_real * 100) and abst == round(abst_real * 100)
    assert set(m["ufs"]) == {"MG", "SP"}
    assert m["exterior"] is not None and m["exterior"][0] >= 0


def test_camada_de_deputado_e_por_partido(publicado):
    m = _ler(publicado / "2022" / "1" / "mapa" / "deputado-federal.json")
    assert m["por"] == "partido"
    assert all(v["chave"] == v["partido"] for v in m["votaveis"])
    assert m["exterior"] is None


def test_deputado_estadual_inclui_distrital(banco_completo, tmp_path):
    # o fixture não tem DF: numa cópia, o Deputado Estadual de SP vira Distrital (cargo 8)
    import shutil

    from eleicoes.marts import construir_marts

    copia = tmp_path / "copia.duckdb"
    shutil.copyfile(banco_completo, copia)
    c = duckdb.connect(str(copia))
    for t in ("votacao_munzona", "votacao_partido_munzona", "detalhe_munzona"):
        c.execute(f"UPDATE staging.{t} SET cd_cargo = 8 WHERE sg_uf = 'SP' AND cd_cargo = 7")
    construir_marts(c)
    gerar_snapshots(c, tmp_path / "out", gerado_em=GERADO_EM)
    c.close()
    m = _ler(tmp_path / "out" / "2022" / "1" / "mapa" / "deputado-estadual.json")
    assert {SAO_PAULO, ITAJUBA} <= set(m["municipios"])
    assert (
        tmp_path / "out" / "2022" / "1" / "municipios" / "SP" / "deputado-estadual.json"
    ).exists()


def test_empate_vira_indice_menos_um(banco_completo, tmp_path):
    import shutil

    copia = tmp_path / "copia.duckdb"
    shutil.copyfile(banco_completo, copia)
    c = duckdb.connect(str(copia))
    c.execute(
        """UPDATE marts.resultado_municipio SET posicao = 1
           WHERE ano = 2022 AND turno = 1 AND cd_municipio = 46477 AND cd_cargo = 3
             AND posicao = 2"""
    )
    gerar_snapshots(c, tmp_path / "out", gerado_em=GERADO_EM)
    c.close()
    m = _ler(tmp_path / "out" / "2022" / "1" / "mapa" / "governador.json")
    assert m["municipios"][ITAJUBA][0] == -1


def test_detalhe_por_municipio_e_zona(publicado):
    d = _ler(publicado / "2022" / "1" / "municipios" / "MG" / "governador.json")
    assert (d["uf"], d["cargo"], d["por"]) == ("MG", "governador", "candidato")
    bh = d["municipios"][BH]
    assert (bh["nome"], bh["codigo_tse"]) == ("Belo Horizonte", 41238)
    assert [z["zona"] for z in bh["zonas"]] == [32, 33]
    # a soma das zonas fecha com o total do município
    for i in range(len(bh["total"]["votos"])):
        chave, votos, _ = bh["total"]["votos"][i]
        assert votos == sum(dict((k, v) for k, v, _ in z["votos"])[chave] for z in bh["zonas"])
    assert bh["total"]["comparecimento"]["aptos"] == sum(
        z["comparecimento"]["aptos"] for z in bh["zonas"]
    )
    assert set(d["votaveis"][bh["total"]["votos"][0][0]]) == {"numero", "nome", "partido"}
    assert "candidatos" not in bh["total"]


def test_zona_que_atende_dois_municipios_e_marcada(publicado):
    d = _ler(publicado / "2022" / "1" / "municipios" / "MG" / "presidente.json")
    (zona_itajuba,) = d["municipios"][ITAJUBA]["zonas"]
    (zona_brazopolis,) = d["municipios"][BRAZOPOLIS]["zonas"]
    assert zona_itajuba["zona"] == zona_brazopolis["zona"] == 134
    assert zona_itajuba["outros_municipios"] == zona_brazopolis["outros_municipios"] == 1
    assert d["municipios"][BH]["zonas"][0]["outros_municipios"] == 0


def test_detalhe_de_deputado_tem_partidos_e_top_candidatos(publicado):
    from eleicoes.snapshots import TOP_CANDIDATOS_MAPA

    d = _ler(publicado / "2022" / "1" / "municipios" / "SP" / "deputado-estadual.json")
    sp = d["municipios"][SAO_PAULO]
    assert d["por"] == "partido"
    assert {k for k, _, _ in sp["total"]["votos"]} <= {"PT", "PL", "PSDB", "PSOL"}
    assert 0 < len(sp["total"]["candidatos"]) <= TOP_CANDIDATOS_MAPA
    assert all(z["candidatos"] for z in sp["zonas"])
    assert sum(v for _, v, _ in sp["total"]["votos"]) > sum(
        v for _, v, _ in sp["total"]["candidatos"]
    )  # partidos incluem a legenda


def test_fotos_so_dos_presidentes_e_referenciadas(publicado):
    b = _ler(publicado / "2022" / "1" / "brasil.json")
    fotos = {c["numero"]: c["foto"] for c in b["presidente"]["candidatos"]}
    # arquivo nomeado pelo número de urna (o sequencial do TSE não é publicado)
    assert fotos[13] == "fotos/2022/13.jpg"
    assert fotos[15] is None  # o fixture não tem a foto do último presidenciável
    assert (publicado / fotos[13]).read_bytes()[:2] == b"\xff\xd8"  # JPEG
    publicadas = {a for a in _arvore(publicado) if a.startswith("fotos/")}
    assert publicadas == {f"fotos/{ano}/{n}.jpg" for ano in (2018, 2022) for n in (13, 22)}


def test_sequencial_do_tse_parecido_com_cpf_nao_vai_para_os_snapshots(banco_completo, tmp_path):
    # Caso real (ETL 2018): sq_candidato de 11 dígitos que passa no DV de CPF.
    import shutil

    from eleicoes.marts import construir_marts
    from tests.test_lgpd import CPF_VALIDO

    copia = tmp_path / "copia.duckdb"
    shutil.copyfile(banco_completo, copia)
    c = duckdb.connect(str(copia))
    for t in ("votacao_munzona", "candidatos"):
        c.execute(
            f"UPDATE staging.{t} SET sq_candidato = {CPF_VALIDO} "
            "WHERE ano = 2022 AND cd_cargo = 3 AND nr_candidato = 30"
        )
    construir_marts(c)
    gerar_snapshots(c, tmp_path / "out", gerado_em=GERADO_EM)
    c.close()
    assert verificar_snapshots(tmp_path / "out") == []
    m = _ler(tmp_path / "out" / "2022" / "1" / "mapa" / "governador.json")
    assert {v["chave"] for v in m["votaveis"]} <= {
        "MG-30",
        "MG-13",
        "MG-45",
        "SP-45",
        "SP-13",
        "SP-22",
    }


def test_malha_publicada_tem_os_municipios_das_camadas(publicado):
    topo = _ler(publicado / "geo" / "municipios.topo.json")
    ids = {str(g["id"]) for g in topo["objects"]["municipios"]["geometries"]}
    for camada in publicado.glob("*/*/mapa/*.json"):
        assert set(_ler(camada)["municipios"]) <= ids


def test_arquivos_do_mapa_sao_compactos(publicado):
    corpo = (publicado / "2022" / "1" / "mapa" / "presidente.json").read_text(encoding="utf-8")
    assert "\n " not in corpo and '": ' not in corpo


def test_municipio_sem_poligono_vai_a_parte(banco_completo, tmp_path):
    # Brazópolis declarado sem polígono e retirado da malha: continua nos dados,
    # passa no gate e aparece em `sem_geometria` com nome e UF.
    import shutil

    from eleicoes.marts import carregar_excecoes, construir_marts
    from eleicoes.qualidade import executar

    copia = tmp_path / "copia.duckdb"
    shutil.copyfile(banco_completo, copia)
    c = duckdb.connect(str(copia))
    c.execute(
        """UPDATE staging.ibge_malha
           SET topojson = replace(topojson, '"codarea": "3108909"', '"codarea": "9999999"')"""
    )
    construir_marts(c, excecoes={**carregar_excecoes(), "sem_poligono": [3108909]})
    rel = executar(c, 2022, 1, ufs=("MG", "SP"))
    assert rel.ok, rel.texto()
    gerar_snapshots(c, tmp_path / "out", gerado_em=GERADO_EM)
    c.close()
    m = _ler(tmp_path / "out" / "2022" / "1" / "mapa" / "presidente.json")
    assert m["sem_geometria"] == {BRAZOPOLIS: {"nome": "Brazópolis", "uf": "MG"}}
    assert BRAZOPOLIS in m["municipios"]
