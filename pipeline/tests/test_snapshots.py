import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from eleicoes import snapshots
from eleicoes.lgpd import verificar_snapshots
from eleicoes.snapshots import SCHEMA_VERSAO, gerar_snapshots

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


def test_manifesto(publicado):
    m = _ler(publicado / "manifest.json")
    assert m["schema_versao"] == SCHEMA_VERSAO
    assert m["gerado_em"] == GERADO_EM
    assert m["eleicoes"] == [{"ano": 2018, "turnos": [1]}, {"ano": 2022, "turnos": [1, 2]}]
    assert m["municipio"] == {"codigo": 46477, "nome": "ITAJUBÁ", "uf": "MG"}
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
    assert 0 < b["comparecimento"]["pct_comparecimento"] < 100


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
