import csv

import pytest

from eleicoes import esquema, staging
from eleicoes.staging import SchemaDivergente, carregar_particao
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
