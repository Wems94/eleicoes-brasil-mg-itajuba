from pathlib import Path

import duckdb
import pytest

from eleicoes import esquema
from eleicoes.tse_csv import (
    Coluna,
    ColunaObrigatoriaAusente,
    Tabela,
    ler_cabecalho,
    resolver,
    select_sql,
)

TSE = Path(__file__).parent / "fixtures" / "tse"


def _ler(tabela: Tabela, *arquivos: Path) -> list[dict]:
    con = duckdb.connect()
    rel = con.sql(select_sql(tabela, list(arquivos)))
    return [dict(zip(rel.columns, linha, strict=True)) for linha in rel.fetchall()]


def _tipos(tabela: Tabela, *arquivos: Path) -> list[tuple[str, str]]:
    con = duckdb.connect()
    rel = con.sql(select_sql(tabela, list(arquivos)))
    return list(zip(rel.columns, [str(t) for t in rel.types], strict=True))


def _csv(path: Path, linhas: list[str]) -> Path:
    path.write_bytes(("\n".join(linhas) + "\n").encode("latin-1"))
    return path


MUNZONA_2018 = TSE / "2018" / "votacao_candidato_munzona_2018_MG.csv"
MUNZONA_2022 = TSE / "2022" / "votacao_candidato_munzona_2022_MG.csv"


def test_cabecalho_lido_em_latin1():
    cab = ler_cabecalho(MUNZONA_2018)
    assert cab[:3] == ["DT_GERACAO", "HH_GERACAO", "ANO_ELEICAO"]
    assert "CD_SITUACAO_DIPLOMA" in cab
    assert "CD_SITUACAO_DCONST_DIPLOMA" in ler_cabecalho(MUNZONA_2022)


def test_mesmo_schema_em_2018_e_2022():
    tipos_2018 = _tipos(esquema.VOTACAO_MUNZONA, MUNZONA_2018)
    tipos_2022 = _tipos(esquema.VOTACAO_MUNZONA, MUNZONA_2022)
    assert tipos_2018 == tipos_2022
    assert [c for c, _ in tipos_2018] == [c.nome for c in esquema.VOTACAO_MUNZONA.colunas]


def test_aliasing_absorve_nome_de_coluna_que_mudou_entre_anos():
    m18 = resolver(esquema.VOTACAO_MUNZONA, ler_cabecalho(MUNZONA_2018))
    m22 = resolver(esquema.VOTACAO_MUNZONA, ler_cabecalho(MUNZONA_2022))
    assert m18["cd_situacao_diploma"] == "CD_SITUACAO_DIPLOMA"
    assert m22["cd_situacao_diploma"] == "CD_SITUACAO_DCONST_DIPLOMA"
    l18 = _ler(esquema.VOTACAO_MUNZONA, MUNZONA_2018)
    l22 = _ler(esquema.VOTACAO_MUNZONA, MUNZONA_2022)
    # CD_SITUACAO_DIPLOMA (2018) e CD_SITUACAO_DCONST_DIPLOMA (2022) -> mesma coluna,
    # e o -3 do TSE vira nulo nas duas
    assert {r["cd_situacao_diploma"] for r in l18} == {None}
    assert {r["cd_situacao_diploma"] for r in l22} == {None}
    assert {r["ds_situacao_diploma"] for r in l22} == {None}  # "#NE"


def test_federacao_em_2018_e_nula():
    linhas = _ler(esquema.VOTACAO_MUNZONA, MUNZONA_2018)
    assert linhas
    assert {r["nr_federacao"] for r in linhas} == {None}
    assert {r["sg_federacao"] for r in linhas} == {None}


def test_federacao_em_2022_preenchida_para_quem_federou():
    linhas = _ler(esquema.VOTACAO_MUNZONA, MUNZONA_2022)
    pt = {r["nr_federacao"] for r in linhas if r["sg_partido"] == "PT"}
    outros = {r["nr_federacao"] for r in linhas if r["sg_partido"] != "PT"}
    assert pt == {1}
    assert outros == {None}


def test_nome_com_acento_vira_utf8():
    linhas = _ler(esquema.VOTACAO_MUNZONA, MUNZONA_2022)
    assert "ITAJUBÁ" in {r["nm_municipio"] for r in linhas}


def test_marcadores_de_nulo(tmp_path):
    tabela = Tabela(
        "t",
        (
            Coluna("texto", aliases=("A",)),
            Coluna("codigo", "INTEGER", aliases=("B",), codigo=True),
            Coluna("quantidade", "INTEGER", aliases=("C",)),
        ),
    )
    arq = _csv(
        tmp_path / "x.csv",
        [
            '"A";"B";"C"',
            '"#NULO#";-1;-1',
            '"#NULO";-3;0',
            '"#NE#";"7";3',
            '"#NE";"";4',
            '"  ok  ";8;5',
        ],
    )
    linhas = _ler(tabela, arq)
    assert [r["texto"] for r in linhas] == [None, None, None, None, "ok"]
    assert [r["codigo"] for r in linhas] == [None, None, 7, None, 8]
    # -1 só é marcador em campos de código
    assert [r["quantidade"] for r in linhas] == [-1, 0, 3, 4, 5]


def test_coluna_opcional_ausente_vira_nulo_tipado(tmp_path):
    tabela = Tabela(
        "t",
        (
            Coluna("ano", "INTEGER", aliases=("ANO_ELEICAO", "AA_ELEICAO"), obrigatoria=True),
            Coluna("nr_federacao", "INTEGER", aliases=("NR_FEDERACAO",), codigo=True),
        ),
    )
    arq = _csv(tmp_path / "legado.csv", ['"AA_ELEICAO";"OUTRA"', '2018;"x"'])
    assert _ler(tabela, arq) == [{"ano": 2018, "nr_federacao": None}]
    assert _tipos(tabela, arq) == [("ano", "INTEGER"), ("nr_federacao", "INTEGER")]


def test_primeiro_alias_existente_tem_prioridade():
    tabela = Tabela("t", (Coluna("x", aliases=("NAO_EXISTE", "B", "A")),))
    assert resolver(tabela, ["A", "B"]) == {"x": "B"}


def test_coluna_obrigatoria_ausente_informa_tabela_coluna_e_nomes(tmp_path):
    arq = _csv(tmp_path / "x.csv", ['"ANO_ELEICAO";"NR_TURNO"', "2022;1"])
    with pytest.raises(ColunaObrigatoriaAusente) as exc:
        select_sql(esquema.VOTACAO_MUNZONA, [arq])
    msg = str(exc.value)
    assert "votacao_munzona" in msg
    assert "sg_uf" in msg
    assert "SG_UF" in msg


def test_colunas_nao_declaradas_nunca_sao_lidas():
    """Allowlist (D3): CPF, e-mail, nascimento e título não entram no staging."""
    arq = TSE / "2022" / "consulta_cand_2022_MG.csv"
    assert "NR_CPF_CANDIDATO" in ler_cabecalho(arq)
    sql = select_sql(esquema.CANDIDATOS, [arq])
    for proibida in ("NR_CPF_CANDIDATO", "DS_EMAIL", "DT_NASCIMENTO", "NR_TITULO_ELEITORAL"):
        assert proibida not in sql
    linhas = _ler(esquema.CANDIDATOS, arq)
    valores = {str(v) for r in linhas for v in r.values()}
    assert not any("@" in v for v in valores)


def test_varios_arquivos_com_cabecalhos_diferentes(tmp_path):
    tabela = Tabela(
        "t",
        (
            Coluna("uf", aliases=("SG_UF",), obrigatoria=True),
            Coluna("fed", "INTEGER", aliases=("NR_FEDERACAO",), codigo=True),
        ),
    )
    a = _csv(tmp_path / "a.csv", ['"SG_UF";"NR_FEDERACAO"', '"MG";1'])
    b = _csv(tmp_path / "b.csv", ['"SG_UF"', '"SP"'])
    linhas = sorted(_ler(tabela, a, b), key=lambda r: r["uf"])
    assert linhas == [{"uf": "MG", "fed": 1}, {"uf": "SP", "fed": None}]
