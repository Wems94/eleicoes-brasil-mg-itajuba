import json

import duckdb
import pytest

from eleicoes import geometria


@pytest.fixture
def con(banco_completo):
    c = duckdb.connect(str(banco_completo), read_only=True)
    yield c
    c.close()


def test_municipios_ganham_id_nome_e_uf(con):
    topo = geometria.montar(con)

    geos = topo["objects"]["municipios"]["geometries"]
    assert [g["id"] for g in geos] == [3106200, 3108909, 3121258, 3132404, 3550308]
    itajuba = next(g for g in geos if g["id"] == 3132404)
    assert itajuba["properties"] == {"nome": "Itajubá", "uf": "MG"}
    assert itajuba["type"] == "Polygon" and itajuba["arcs"]


def test_arcos_e_transformacao_preservados(con):
    original = json.loads(con.execute("SELECT topojson FROM staging.ibge_malha").fetchone()[0])
    topo = geometria.montar(con)
    assert topo["arcs"] == original["arcs"]
    assert topo["transform"] == original["transform"]


def test_serializacao_compacta_e_deterministica(con):
    a = geometria.serializar(geometria.montar(con))
    b = geometria.serializar(geometria.montar(con))
    assert a == b
    assert b" " not in a.replace(b"Belo Horizonte", b"").replace(b"Delfim Moreira", b"").replace(
        b"S\xc3\xa3o Paulo", b""
    )


def test_tamanho_do_fixture_dentro_do_orcamento(con):
    # O orçamento com dados reais é conferido no scripts/validar_real.py.
    assert geometria.tamanho_gzip(geometria.serializar(geometria.montar(con))) < (
        geometria.ORCAMENTO_GZIP
    )


def test_sem_malha_no_staging_falha_com_mensagem(tmp_path):
    c = duckdb.connect(str(tmp_path / "vazio.duckdb"))
    c.execute("CREATE SCHEMA staging")
    c.execute("CREATE TABLE staging.ibge_malha (topojson VARCHAR)")
    with pytest.raises(geometria.MalhaAusente):
        geometria.montar(c)
