import duckdb
import pytest

from eleicoes.staging import (
    MunicipioNaoEncontrado,
    Recorte,
    carregar_particao,
    criar_tabelas,
    resolver_municipio,
)
from tests.conftest import TSE

ITAJUBA = Recorte(uf="MG", municipio="ITAJUBÁ")


def test_recorte_padrao_vem_da_configuracao():
    assert Recorte.carregar() == ITAJUBA


def test_secoes_apenas_de_itajuba(con, zips, trabalho):
    resumo = carregar_particao(con, 2022, 1, zips(), trabalho)

    assert resumo.cd_municipio == 46477
    for tabela in ("votacao_secao", "detalhe_secao", "locais_votacao"):
        assert con.execute(
            f"SELECT DISTINCT sg_uf, cd_municipio, nm_municipio FROM staging.{tabela}"
        ).fetchall() == [("MG", 46477, "ITAJUBÁ")], tabela


def test_visao_por_uf_mantem_todos_os_municipios(con, zips, trabalho):
    carregar_particao(con, 2022, 1, zips(), trabalho)

    ufs = {
        r[0] for r in con.execute("SELECT DISTINCT sg_uf FROM staging.votacao_munzona").fetchall()
    }
    assert ufs == {"MG", "SP", "ZZ"}


def test_presidente_vem_do_arquivo_br_quando_falta_no_de_mg(con, zips, trabalho):
    resumo = carregar_particao(con, 2022, 1, zips(), trabalho)

    assert resumo.fallback_presidente
    cargos = {
        r[0] for r in con.execute("SELECT DISTINCT cd_cargo FROM staging.votacao_secao").fetchall()
    }
    assert cargos == {1, 3, 5, 6, 7}
    assert con.execute(
        "SELECT count(DISTINCT nr_secao) FROM staging.detalhe_secao WHERE cd_cargo = 1"
    ).fetchone() == (4,)


def test_sem_fallback_quando_mg_ja_traz_presidente(con, zips, trabalho):
    mg = (TSE / "2022" / "votacao_secao_2022_MG.csv").read_bytes()
    br = (TSE / "2022" / "votacao_secao_2022_BR.csv").read_bytes()
    mg_com_presidente = mg + br.split(b"\n", 1)[1]
    arquivos = zips(substituir={"votacao_secao_2022_MG.csv": mg_com_presidente})

    resumo = carregar_particao(con, 2022, 1, arquivos, trabalho)

    assert not resumo.fallback_presidente
    duplicadas = con.execute(
        """SELECT count(*) FROM (
             SELECT nr_secao, cd_cargo, nr_votavel FROM staging.votacao_secao
             GROUP BY ALL HAVING count(*) > 1)"""
    ).fetchone()
    assert duplicadas == (0,)


def test_segundo_turno_de_itajuba_so_tem_presidente(con, zips, trabalho):
    carregar_particao(con, 2022, 2, zips(), trabalho)

    assert con.execute("SELECT DISTINCT cd_cargo FROM staging.votacao_secao").fetchall() == [(1,)]


def test_local_sem_coordenada_fica_nulo(con, zips, trabalho):
    carregar_particao(con, 2022, 1, zips(), trabalho)

    assert con.execute(
        "SELECT nr_latitude, nr_longitude FROM staging.locais_votacao WHERE nr_secao = 26"
    ).fetchall() == [(None, None)]
    assert con.execute(
        "SELECT nr_latitude FROM staging.locais_votacao WHERE nr_secao = 18"
    ).fetchone() == (pytest.approx(-22.4267816),)


# --- resolução do código pelo nome ---------------------------------------------


@pytest.fixture
def con_munzona():
    c = duckdb.connect()
    criar_tabelas(c)
    c.execute(
        """INSERT INTO staging.detalhe_munzona (ano, turno, sg_uf, cd_municipio, nm_municipio,
             nr_zona, cd_cargo, qt_aptos, qt_comparecimento, qt_abstencoes, qt_votos_brancos,
             qt_votos_nulos)
           VALUES (2022, 1, 'MG', 46477, 'ITAJUBÁ', 134, 3, 1, 1, 0, 0, 0),
                  (2022, 1, 'SP', 99999, 'ITAJUBA', 1, 3, 1, 1, 0, 0, 0),
                  (2022, 1, 'MG', 41238, 'BELO HORIZONTE', 32, 3, 1, 1, 0, 0, 0)"""
    )
    yield c
    c.close()


def test_resolucao_ignora_homonimo_de_outra_uf(con_munzona):
    assert resolver_municipio(con_munzona, 2022, 1, ITAJUBA) == 46477


def test_resolucao_nao_diferencia_acento_nem_caixa(con_munzona):
    assert resolver_municipio(con_munzona, 2022, 1, Recorte("MG", "Itajuba")) == 46477


def test_municipio_inexistente_falha(con_munzona):
    with pytest.raises(MunicipioNaoEncontrado, match="PARAÍSO/MG"):
        resolver_municipio(con_munzona, 2022, 1, Recorte("MG", "PARAÍSO"))


def test_municipio_ambiguo_falha(con_munzona):
    con_munzona.execute(
        """INSERT INTO staging.detalhe_munzona (ano, turno, sg_uf, cd_municipio, nm_municipio,
             nr_zona, cd_cargo, qt_aptos, qt_comparecimento, qt_abstencoes, qt_votos_brancos,
             qt_votos_nulos)
           VALUES (2022, 1, 'MG', 11111, 'Itajubá', 1, 3, 1, 1, 0, 0, 0)"""
    )
    with pytest.raises(MunicipioNaoEncontrado, match="46477"):
        resolver_municipio(con_munzona, 2022, 1, ITAJUBA)
