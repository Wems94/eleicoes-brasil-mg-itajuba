import pytest

from eleicoes.fontes import AnoNaoSuportado, Catalogo

BASE = "https://cdn.tse.jus.br/estatistica/sead/odsele/"


@pytest.fixture(scope="module")
def catalogo() -> Catalogo:
    return Catalogo.carregar()


def test_anos_suportados(catalogo):
    assert catalogo.anos == (2018, 2022, 2026)


def test_ano_nao_suportado_explica_os_anos_validos(catalogo):
    with pytest.raises(AnoNaoSuportado, match="2018, 2022, 2026"):
        catalogo.resolver(2020)


@pytest.mark.parametrize(
    ("nome", "ano", "caminho"),
    [
        (
            "votacao_candidato_munzona",
            2022,
            "votacao_candidato_munzona/votacao_candidato_munzona_2022.zip",
        ),
        (
            "detalhe_votacao_munzona",
            2018,
            "detalhe_votacao_munzona/detalhe_votacao_munzona_2018.zip",
        ),
        ("votacao_secao_mg", 2026, "votacao_secao/votacao_secao_2026_MG.zip"),
        ("votacao_secao_br", 2022, "votacao_secao/votacao_secao_2022_BR.zip"),
        ("detalhe_votacao_secao", 2022, "detalhe_votacao_secao/detalhe_votacao_secao_2022.zip"),
        ("consulta_cand", 2018, "consulta_cand/consulta_cand_2018.zip"),
        ("locais_votacao", 2026, "eleitorado_locais_votacao/eleitorado_local_votacao_2026.zip"),
    ],
)
def test_resolve_url_por_ano(catalogo, nome, ano, caminho):
    fonte = catalogo.fonte(nome, ano)
    assert fonte.url == BASE + caminho
    assert fonte.ano == ano
    assert fonte.arquivo == caminho.rsplit("/", 1)[1]


def test_resolver_devolve_todas_as_fontes_do_ano(catalogo):
    fontes = catalogo.resolver(2022)
    assert {f.nome for f in fontes} == {
        "votacao_candidato_munzona",
        "detalhe_votacao_munzona",
        "votacao_secao_mg",
        "votacao_secao_br",
        "detalhe_votacao_secao",
        "consulta_cand",
        "locais_votacao",
    }
    assert all(f.ano == 2022 for f in fontes)


def test_obrigatoriedade(catalogo):
    assert catalogo.fonte("votacao_candidato_munzona", 2022).obrigatoria
    assert not catalogo.fonte("locais_votacao", 2022).obrigatoria


def test_membros_por_uf_excluem_o_consolidado_brasil(catalogo):
    fonte = catalogo.fonte("votacao_candidato_munzona", 2022)
    nomes = [
        "votacao_candidato_munzona_2022_MG.csv",
        "votacao_candidato_munzona_2022_BR.csv",
        "votacao_candidato_munzona_2022_BRASIL.csv",
        "leiame.pdf",
    ]
    assert fonte.selecionar_membros(nomes) == [
        "votacao_candidato_munzona_2022_MG.csv",
        "votacao_candidato_munzona_2022_BR.csv",
    ]


def test_membros_de_secao_ficam_restritos_a_mg_e_br(catalogo):
    fonte = catalogo.fonte("detalhe_votacao_secao", 2022)
    nomes = [
        "detalhe_votacao_secao_2022_SP.csv",
        "detalhe_votacao_secao_2022_MG.csv",
        "detalhe_votacao_secao_2022_BR.csv",
        "detalhe_votacao_secao_2022_BRASIL.csv",
    ]
    assert fonte.selecionar_membros(nomes) == [
        "detalhe_votacao_secao_2022_MG.csv",
        "detalhe_votacao_secao_2022_BR.csv",
    ]


def test_base_url_pode_ser_sobrescrita():
    cat = Catalogo.carregar(base_url="http://127.0.0.1:9999/")
    assert cat.fonte("consulta_cand", 2022).url == (
        "http://127.0.0.1:9999/consulta_cand/consulta_cand_2022.zip"
    )


@pytest.mark.parametrize(
    ("ano", "nomes", "esperado"),
    [
        # 2018/2022: arquivo único
        (
            2022,
            ["eleitorado_local_votacao_2022.csv", "leiame.pdf"],
            ["eleitorado_local_votacao_2022.csv"],
        ),
        # 2026: dividido por UF, com consolidado _BRASIL; só MG interessa ao recorte
        (
            2026,
            [
                "eleitorado_local_votacao_2026_BRASIL.csv",
                "eleitorado_local_votacao_2026_MG.csv",
                "eleitorado_local_votacao_2026_ZZ.csv",
                "leiame.pdf",
            ],
            ["eleitorado_local_votacao_2026_MG.csv"],
        ),
    ],
)
def test_membros_de_locais_nos_dois_layouts(catalogo, ano, nomes, esperado):
    assert catalogo.fonte("locais_votacao", ano).selecionar_membros(nomes) == esperado
