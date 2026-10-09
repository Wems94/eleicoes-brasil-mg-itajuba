import csv
import logging
import zipfile

import pytest

from eleicoes import esquema, staging
from eleicoes.staging import SchemaDivergente, SemDados, carregar_particao
from tests.conftest import TSE


def _contagens(con) -> dict[tuple[str, int, int], int]:
    out = {}
    for t in esquema.TABELAS:
        for ano, turno, n in con.execute(
            f"SELECT ano, turno, count(*) FROM staging.{t.nome} GROUP BY ALL"
        ).fetchall():
            out[(t.nome, ano, turno)] = n
    return out


def _linhas_csv(nome: str, turno: int) -> int:
    with (TSE / "2022" / nome).open(encoding="latin-1") as f:
        return sum(1 for r in csv.DictReader(f, delimiter=";") if r["NR_TURNO"] == str(turno))


def test_carga_cria_todas_as_tabelas_de_staging(con, zips, trabalho):
    resumo = carregar_particao(con, 2022, 1, zips(), trabalho)

    tabelas = {
        r[0]
        for r in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'staging'"
        ).fetchall()
    }
    assert tabelas == {t.nome for t in esquema.TABELAS}
    assert all(resumo.linhas[t.nome] > 0 for t in esquema.TABELAS)


def test_somente_o_turno_pedido_e_carregado(con, zips, trabalho):
    carregar_particao(con, 2022, 2, zips(), trabalho)

    for t in esquema.TABELAS:
        assert con.execute(f"SELECT DISTINCT ano, turno FROM staging.{t.nome}").fetchall() == [
            (2022, 2)
        ]


def test_membro_brasil_nao_duplica_votos(con, zips, trabalho):
    carregar_particao(con, 2022, 1, zips(), trabalho)

    esperado = sum(
        _linhas_csv(f"votacao_candidato_munzona_2022_{m}.csv", 1) for m in ("MG", "SP", "BR")
    )
    (n,) = con.execute("SELECT count(*) FROM staging.votacao_munzona").fetchone()
    assert n == esperado


def test_reprocessamento_idempotente(con, zips, trabalho):
    arquivos = zips()
    carregar_particao(con, 2022, 1, arquivos, trabalho)
    antes = _contagens(con)

    carregar_particao(con, 2022, 1, arquivos, trabalho)

    assert _contagens(con) == antes


def test_reprocessar_um_turno_preserva_as_outras_particoes(con, zips, trabalho):
    arquivos_2022 = zips(2022)
    carregar_particao(con, 2022, 1, arquivos_2022, trabalho)
    carregar_particao(con, 2022, 2, arquivos_2022, trabalho)
    carregar_particao(con, 2018, 1, zips(2018), trabalho)
    antes = _contagens(con)
    turno2 = con.execute(
        "SELECT * FROM staging.votacao_munzona WHERE turno = 2 ORDER BY ALL"
    ).fetchall()

    carregar_particao(con, 2022, 1, arquivos_2022, trabalho)

    assert _contagens(con) == antes
    assert (
        con.execute("SELECT * FROM staging.votacao_munzona WHERE turno = 2 ORDER BY ALL").fetchall()
        == turno2
    )
    assert {k[1:] for k in antes if k[0] == "votacao_munzona"} == {(2022, 1), (2022, 2), (2018, 1)}


def test_falha_no_meio_da_carga_preserva_a_particao_anterior(con, zips, trabalho, monkeypatch):
    arquivos = zips()
    carregar_particao(con, 2022, 1, arquivos, trabalho)
    antes = _contagens(con)

    inserir_original = staging._inserir

    def inserir_com_falha(con_, tabela, *args, **kwargs):
        if tabela is esquema.CANDIDATOS:
            raise RuntimeError("falha simulada")
        return inserir_original(con_, tabela, *args, **kwargs)

    monkeypatch.setattr(staging, "_inserir", inserir_com_falha)
    with pytest.raises(RuntimeError, match="falha simulada"):
        carregar_particao(con, 2022, 1, arquivos, trabalho)

    assert _contagens(con) == antes


def test_fonte_opcional_ausente_e_registrada(con, zips, trabalho):
    resumo = carregar_particao(con, 2022, 1, zips(sem=["locais_votacao"]), trabalho)

    assert resumo.fontes_ausentes == ["locais_votacao"]
    assert resumo.linhas["locais_votacao"] == 0
    assert resumo.linhas["votacao_munzona"] > 0


def test_arquivos_extraidos_sao_removidos(con, zips, trabalho):
    carregar_particao(con, 2022, 1, zips(), trabalho)
    assert list(trabalho.iterdir()) == []


def test_schema_divergente_e_detectado(con, zips, trabalho):
    con.execute("CREATE SCHEMA staging")
    con.execute("CREATE TABLE staging.votacao_munzona (ano INTEGER, turno INTEGER)")

    with pytest.raises(SchemaDivergente, match="votacao_munzona"):
        carregar_particao(con, 2022, 1, zips(), trabalho)


def _zip_com_membros(caminho, membros: dict[str, bytes]) -> None:
    with zipfile.ZipFile(caminho, "w") as z:
        for nome, corpo in membros.items():
            z.writestr(nome, corpo)


def test_fonte_opcional_com_layout_inesperado_vira_aviso(con, zips, trabalho, caplog):
    arquivos = zips()
    _zip_com_membros(arquivos["locais_votacao"].caminho, {"layout_novo.csv": b"x\n"})

    with caplog.at_level(logging.WARNING):
        resumo = carregar_particao(con, 2022, 1, arquivos, trabalho)

    assert resumo.fontes_ausentes == ["locais_votacao"]
    assert "eleitorado_local_votacao_2022.zip" in caplog.text


def test_fonte_obrigatoria_com_layout_inesperado_falha(con, zips, trabalho):
    arquivos = zips()
    _zip_com_membros(arquivos["votacao_secao_mg"].caminho, {"layout_novo.csv": b"x\n"})

    with pytest.raises(FileNotFoundError, match="votacao_secao_2022_MG.zip"):
        carregar_particao(con, 2022, 1, arquivos, trabalho)


def test_turno_sem_dados_falha_com_mensagem_clara_e_preserva_o_banco(con, zips, trabalho):
    arquivos = zips()
    carregar_particao(con, 2022, 1, arquivos, trabalho)
    antes = _contagens(con)

    def sem_turno_2(nome: str) -> bytes:  # remove as linhas com NR_TURNO (6ª coluna) = 2
        linhas = (TSE / "2022" / nome).read_bytes().splitlines()
        return b"\n".join(lin for lin in linhas if lin.split(b";")[5] != b"2") + b"\n"

    substituir = {
        f"{dataset}_2022_{m}.csv": sem_turno_2(f"{dataset}_2022_{m}.csv")
        for dataset in ("votacao_candidato_munzona", "detalhe_votacao_munzona")
        for m in ("MG", "SP", "BR")
    }

    with pytest.raises(SemDados, match="2022 turno 2"):
        carregar_particao(con, 2022, 2, zips(substituir=substituir), trabalho)

    assert _contagens(con) == antes


def test_detalhe_munzona_fecha_com_os_votos_sub_judice(con, zips, trabalho):
    """válidos + brancos + nulos + anulados + sub judice = comparecimento × votos por eleitor.

    Em 2026 há milhares de linhas com votos em candidatos sub judice
    (QT_TOTAL_VOTOS_ANUL_SUBJUD); sem essa coluna a soma não fecha.
    """
    det = (TSE / "2022" / "detalhe_votacao_munzona_2022_MG.csv").read_bytes().splitlines()
    cab = det[0].split(b";")
    i_subjud, i_validos, i_votos = (
        cab.index(b'"QT_TOTAL_VOTOS_ANUL_SUBJUD"'),
        cab.index(b'"QT_TOTAL_VOTOS_VALIDOS"'),
        cab.index(b'"QT_VOTOS"'),
    )
    linhas = [det[0]]
    for lin in det[1:]:  # move 7 votos válidos para sub judice em cada linha
        c = lin.split(b";")
        c[i_validos] = str(int(c[i_validos]) - 7).encode()
        c[i_subjud] = b"7"
        assert c[i_votos]
        linhas.append(b";".join(c))
    arquivos = zips(substituir={"detalhe_votacao_munzona_2022_MG.csv": b"\n".join(linhas) + b"\n"})
    carregar_particao(con, 2022, 1, arquivos, trabalho)

    assert con.execute(
        "SELECT DISTINCT qt_votos_anulados_subjudice FROM staging.detalhe_munzona"
        " WHERE sg_uf = 'MG' AND cd_cargo <> 1"  # Presidente de MG vem do membro _BR
    ).fetchall() == [(7,)]
    assert con.execute(
        """SELECT count(*) FROM staging.detalhe_munzona
           WHERE qt_votos_validos + qt_votos_brancos + qt_votos_nulos
                 + coalesce(qt_votos_anulados, 0) + coalesce(qt_votos_anulados_subjudice, 0)
                 <> qt_comparecimento  -- 2022: 1 voto por eleitor em todo cargo
           """
    ).fetchone() == (0,)
