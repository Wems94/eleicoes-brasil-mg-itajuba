import csv
from collections import defaultdict

import duckdb
import pytest

from eleicoes.marts import TABELAS_MARTS, construir_marts
from eleicoes.staging import carregar_particao
from tests.conftest import TSE, montar_zips

CANDIDATO_E_LEGENDA = "tipo_votavel IN ('candidato', 'legenda')"


def _csv(ano: int, nome: str) -> list[dict]:
    with (TSE / str(ano) / nome).open(encoding="latin-1") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _soma(linhas, campo, **filtro) -> int:
    return sum(int(r[campo]) for r in linhas if all(r[k] == str(v) for k, v in filtro.items()))


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    """Banco com 2018/1, 2022/1 e 2022/2; compartilhado porque os testes só leem."""
    base = tmp_path_factory.mktemp("marts")
    con = duckdb.connect(str(base / "eleicoes.duckdb"))
    z2022 = montar_zips(2022, base / "raw" / "2022")
    carregar_particao(con, 2018, 1, montar_zips(2018, base / "raw" / "2018"), base / "trabalho")
    carregar_particao(con, 2022, 1, z2022, base / "trabalho")
    carregar_particao(con, 2022, 2, z2022, base / "trabalho")
    construir_marts(con)
    yield con
    con.close()


def _q(con, sql, *params):
    return con.execute(sql, list(params)).fetchall()


def test_todas_as_tabelas_de_marts(db):
    existentes = {
        r[0]
        for r in _q(
            db, "SELECT table_name FROM information_schema.tables WHERE table_schema='marts'"
        )
    }
    assert existentes == set(TABELAS_MARTS)


def test_cargos_com_votos_por_eleitor_do_senado(db):
    assert _q(
        db, "SELECT ano, votos_por_eleitor FROM marts.cargos WHERE cd_cargo = 5 ORDER BY 1"
    ) == [
        (2018, 2),
        (2022, 1),
        (2026, 2),
    ]


# --- UF e Brasil -----------------------------------------------------------------


def test_percentual_sobre_validos_por_uf(db):
    mz = _csv(2022, "votacao_candidato_munzona_2022_MG.csv")
    det = _csv(2022, "detalhe_votacao_munzona_2022_MG.csv")
    votos = _soma(mz, "QT_VOTOS_NOMINAIS_VALIDOS", NR_TURNO=1, CD_CARGO=3, NR_CANDIDATO=30)
    validos = _soma(det, "QT_TOTAL_VOTOS_VALIDOS", NR_TURNO=1, CD_CARGO=3)

    ((v, val, pct),) = _q(
        db,
        """SELECT votos, votos_validos, pct_validos FROM marts.resultado_uf
           WHERE ano = 2022 AND turno = 1 AND sg_uf = 'MG' AND cd_cargo = 3
             AND nr_candidato = 30""",
    )
    assert (v, val) == (votos, validos)
    assert pct == pytest.approx(100 * votos / validos)


def test_majoritarios_somam_100_por_cento(db):
    somas = _q(
        db,
        """SELECT ano, turno, sg_uf, cd_cargo, sum(pct_validos) FROM marts.resultado_uf
           WHERE cd_cargo IN (1, 3, 5) GROUP BY ALL""",
    )
    assert len(somas) > 5
    for *_, s in somas:
        assert s == pytest.approx(100)


def test_proporcionais_tem_parte_dos_validos_na_legenda(db):
    for *_, s in _q(
        db,
        """SELECT ano, turno, sg_uf, cd_cargo, sum(pct_validos) FROM marts.resultado_uf
           WHERE cd_cargo IN (6, 7) GROUP BY ALL""",
    ):
        assert 80 < s < 100


def test_situacao_dos_deputados(db):
    sits = _q(
        db,
        """SELECT posicao, ds_sit_tot_turno FROM marts.resultado_uf
           WHERE ano = 2022 AND turno = 1 AND sg_uf = 'MG' AND cd_cargo = 6 ORDER BY posicao""",
    )
    assert [s for _, s in sits] == ["ELEITO POR QP", "ELEITO POR MÉDIA", "SUPLENTE", "SUPLENTE"]


def test_presidente_nacional_inclui_exterior(db):
    br = _csv(2022, "votacao_candidato_munzona_2022_BR.csv")
    esperado = _soma(br, "QT_VOTOS_NOMINAIS_VALIDOS", NR_TURNO=1, NR_CANDIDATO=13)
    assert {r["SG_UF"] for r in br} == {"MG", "SP", "ZZ"}

    linhas = _q(
        db,
        """SELECT nr_candidato, votos, pct_validos, posicao FROM marts.resultado_brasil
           WHERE ano = 2022 AND turno = 1 ORDER BY posicao""",
    )
    assert dict((n, v) for n, v, _, _ in linhas)[13] == esperado
    assert sum(p for _, _, p, _ in linhas) == pytest.approx(100)
    assert [pos for *_, pos in linhas] == [1, 2, 3]
    assert linhas[0][1] == max(v for _, v, _, _ in linhas)


def test_segundo_turno_nacional_tem_dois_candidatos(db):
    assert _q(db, "SELECT count(*) FROM marts.resultado_brasil WHERE ano = 2022 AND turno = 2") == [
        (2,)
    ]


def test_comparecimento_por_uf(db):
    det = _csv(2022, "detalhe_votacao_munzona_2022_BR.csv")
    aptos = _soma(det, "QT_APTOS", NR_TURNO=1, SG_UF="MG")
    comp = _soma(det, "QT_COMPARECIMENTO", NR_TURNO=1, SG_UF="MG")

    ((a, c, pct, abst),) = _q(
        db,
        """SELECT aptos, comparecimento, pct_comparecimento, pct_abstencao
           FROM marts.comparecimento_uf
           WHERE ano = 2022 AND turno = 1 AND sg_uf = 'MG' AND cd_cargo = 1""",
    )
    assert (a, c) == (aptos, comp)
    assert pct == pytest.approx(100 * comp / aptos)
    assert pct + abst == pytest.approx(100)


# --- Itajubá -------------------------------------------------------------------------


def test_itajuba_por_secao_bate_com_o_munzona(db):
    """Duas fontes independentes do TSE: seção agregada = município/zona."""
    divergentes = _q(
        db,
        """WITH s AS (SELECT ano, turno, cd_cargo, nr_votavel, sum(votos) v
                      FROM marts.itajuba_resultado WHERE tipo_votavel = 'candidato' GROUP BY ALL),
                m AS (SELECT ano, turno, cd_cargo, nr_candidato nr_votavel, sum(qt_votos_nominais) v
                      FROM staging.votacao_munzona WHERE cd_municipio = 46477 GROUP BY ALL)
           SELECT * FROM s FULL JOIN m USING (ano, turno, cd_cargo, nr_votavel)
           WHERE s.v IS DISTINCT FROM m.v AND coalesce(m.v, 0) > 0""",
    )
    assert divergentes == []


def test_itajuba_resultado_por_cargo(db):
    linhas = _q(
        db,
        """SELECT tipo_votavel, nr_votavel, sg_partido, nm_cargo, votos, pct_validos
           FROM marts.itajuba_resultado WHERE ano = 2022 AND turno = 1 AND cd_cargo = 1""",
    )
    tipos = {t for t, *_ in linhas}
    assert tipos == {"candidato", "branco", "nulo"}
    assert {(n, p) for t, n, p, *_ in linhas if t == "candidato"} == {
        (13, "PT"),
        (22, "PL"),
        (15, "MDB"),
    }
    assert {nm for *_, nm, _, _ in linhas} == {"Presidente"}
    assert sum(p for t, *_, p in linhas if t == "candidato") == pytest.approx(100)
    assert all(p is None for t, *_, p in linhas if t in ("branco", "nulo"))


def test_itajuba_legenda_entra_nos_validos_dos_proporcionais(db):
    linhas = _q(
        db,
        f"""SELECT tipo_votavel, sg_partido, pct_validos FROM marts.itajuba_resultado
            WHERE ano = 2022 AND turno = 1 AND cd_cargo = 6 AND {CANDIDATO_E_LEGENDA}""",
    )
    assert {t for t, _, _ in linhas} == {"candidato", "legenda"}
    assert all(p is not None for _, p, _ in linhas)
    assert sum(p for *_, p in linhas) == pytest.approx(100)


@pytest.mark.parametrize(
    ("tabela", "chaves"),
    [
        ("itajuba_zona", "nr_zona"),
        ("itajuba_local", "nr_zona, nr_local_votacao"),
        ("itajuba_secao", "nr_zona, nr_secao"),
    ],
)
def test_niveis_de_itajuba_somam_o_total_e_100_por_cento(db, tabela, chaves):
    assert (
        _q(
            db,
            f"""SELECT ano, turno, cd_cargo, sum(votos) FROM marts.{tabela} GROUP BY ALL
            EXCEPT
            SELECT ano, turno, cd_cargo, sum(votos) FROM marts.itajuba_resultado GROUP BY ALL""",
        )
        == []
    )
    for *_, s in _q(
        db,
        f"""SELECT ano, turno, cd_cargo, {chaves}, sum(pct_validos) FROM marts.{tabela}
            WHERE {CANDIDATO_E_LEGENDA} GROUP BY ALL""",
    ):
        assert s == pytest.approx(100)


def test_locais_de_itajuba_com_coordenadas(db):
    locais = _q(
        db,
        """SELECT DISTINCT nr_local_votacao, nm_local_votacao, nr_latitude, nr_longitude
           FROM marts.itajuba_local WHERE ano = 2022 AND turno = 1 ORDER BY 1""",
    )
    assert locais == [
        (1058, "COLÉGIO XIX DE MARÇO", pytest.approx(-22.4256), pytest.approx(-45.4527)),
        (
            1155,
            "E.E. PROF. RAFAEL MAGALHÃES",
            pytest.approx(-22.4267816),
            pytest.approx(-45.461597),
        ),
    ]


def test_locais_sem_arquivo_de_locais_ficam_sem_coordenada(con, zips, trabalho):
    carregar_particao(con, 2022, 1, zips(sem=["locais_votacao"]), trabalho)
    construir_marts(con)

    assert _q(
        con, "SELECT DISTINCT nm_local_votacao IS NOT NULL, nr_latitude FROM marts.itajuba_local"
    ) == [(True, None)]


def test_comparecimento_de_itajuba_por_secao(db):
    det = _csv(2022, "detalhe_votacao_secao_2022_MG.csv")
    esperado = _soma(det, "QT_COMPARECIMENTO", NR_TURNO=1, CD_MUNICIPIO=46477, CD_CARGO=3)

    ((comp, n),) = _q(
        db,
        """SELECT sum(comparecimento), count(*) FROM marts.itajuba_comparecimento
           WHERE ano = 2022 AND turno = 1 AND cd_cargo = 3""",
    )
    assert (comp, n) == (esperado, 4)


def test_historico_de_itajuba(db):
    anos = _q(
        db,
        "SELECT DISTINCT ano, turno FROM marts.historico_itajuba_partido ORDER BY ALL",
    )
    assert anos == [(2018, 1), (2022, 1), (2022, 2)]
    por_cargo = defaultdict(float)
    for ano, turno, cargo, pct in _q(
        db, "SELECT ano, turno, cd_cargo, pct_validos FROM marts.historico_itajuba_partido"
    ):
        por_cargo[(ano, turno, cargo)] += pct
    assert all(s == pytest.approx(100) for s in por_cargo.values())
    assert _q(
        db,
        """SELECT ano, turno, pct_comparecimento > 0 FROM marts.historico_itajuba_comparecimento
           WHERE cd_cargo = 1 ORDER BY ALL""",
    ) == [(2018, 1, True), (2022, 1, True), (2022, 2, True)]


def test_reconstrucao_e_idempotente(db):
    antes = _q(db, "SELECT * FROM marts.resultado_uf ORDER BY ALL")
    construir_marts(db)
    assert _q(db, "SELECT * FROM marts.resultado_uf ORDER BY ALL") == antes
