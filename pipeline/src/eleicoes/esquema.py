"""Tabelas de staging (schema `staging`) e as colunas aceitas de cada fonte do TSE.

Esta é a allowlist do pipeline: só o que está declarado aqui é lido dos CSVs.
Toda tabela tem `ano` e `turno`, que formam a partição lógica (D4).
"""

from eleicoes.tse_csv import Coluna, Tabela


def _txt(nome: str, *aliases: str, obrigatoria: bool = False) -> Coluna:
    return Coluna(nome, "VARCHAR", aliases, obrigatoria)


def _int(nome: str, *aliases: str, obrigatoria: bool = False, tipo: str = "INTEGER") -> Coluna:
    return Coluna(nome, tipo, aliases, obrigatoria)


def _cod(nome: str, *aliases: str, obrigatoria: bool = False, tipo: str = "INTEGER") -> Coluna:
    """Campo de código: -1 e -3 também são marcadores de nulo."""
    return Coluna(nome, tipo, aliases, obrigatoria, codigo=True)


def _dbl(nome: str, *aliases: str) -> Coluna:
    return Coluna(nome, "DOUBLE", aliases, codigo=True)


_PARTICAO = (
    _int("ano", "ANO_ELEICAO", "AA_ELEICAO", obrigatoria=True),
    _int("turno", "NR_TURNO", obrigatoria=True),
)
_LOCALIZACAO = (
    _txt("sg_uf", obrigatoria=True),
    _int("cd_municipio", obrigatoria=True),
    _txt("nm_municipio", obrigatoria=True),
    _int("nr_zona", obrigatoria=True),
)

VOTACAO_MUNZONA = Tabela(
    "votacao_munzona",
    (
        *_PARTICAO,
        _cod("cd_eleicao"),
        *_LOCALIZACAO,
        _int("cd_cargo", obrigatoria=True),
        _txt("ds_cargo"),
        _int("sq_candidato", obrigatoria=True, tipo="BIGINT"),
        _int("nr_candidato", obrigatoria=True),
        _txt("nm_candidato"),
        _txt("nm_urna_candidato", obrigatoria=True),
        _txt("ds_situacao_candidatura"),
        _cod("cd_situacao_diploma", "CD_SITUACAO_DCONST_DIPLOMA", "CD_SITUACAO_DIPLOMA"),
        _txt("ds_situacao_diploma", "DS_SITUACAO_DCONST_DIPLOMA", "DS_SITUACAO_DIPLOMA"),
        _txt("tp_agremiacao"),
        _cod("nr_partido", obrigatoria=True),
        _txt("sg_partido", obrigatoria=True),
        _txt("nm_partido"),
        _cod("nr_federacao"),
        _txt("nm_federacao"),
        _txt("sg_federacao"),
        _cod("sq_coligacao", tipo="BIGINT"),
        _txt("nm_coligacao"),
        _txt("ds_composicao_coligacao"),
        _txt("st_voto_em_transito"),
        _txt("nm_tipo_destinacao_votos"),
        _int("qt_votos_nominais", obrigatoria=True),
        _int("qt_votos_nominais_validos"),
        _cod("cd_sit_tot_turno"),
        _txt("ds_sit_tot_turno"),
    ),
)

DETALHE_MUNZONA = Tabela(
    "detalhe_munzona",
    (
        *_PARTICAO,
        *_LOCALIZACAO,
        _int("cd_cargo", obrigatoria=True),
        _txt("ds_cargo"),
        _txt("st_voto_em_transito"),
        _int("qt_aptos", obrigatoria=True),
        _int("qt_secoes", "QT_TOTAL_SECOES", "QT_SECOES"),
        _int("qt_comparecimento", obrigatoria=True),
        _int("qt_abstencoes", obrigatoria=True),
        _int("qt_votos", "QT_VOTOS"),
        _int("qt_votos_validos", "QT_TOTAL_VOTOS_VALIDOS"),
        _int("qt_votos_nominais", "QT_VOTOS_NOMINAIS_VALIDOS", "QT_VOTOS_NOMINAIS"),
        _int("qt_votos_legenda", "QT_TOTAL_VOTOS_LEG_VALIDOS", "QT_VOTOS_LEGENDA"),
        _int("qt_votos_brancos", obrigatoria=True),
        _int("qt_votos_nulos", "QT_TOTAL_VOTOS_NULOS", "QT_VOTOS_NULOS", obrigatoria=True),
        _int("qt_votos_anulados", "QT_TOTAL_VOTOS_ANULADOS", "QT_VOTOS_ANULADOS"),
    ),
)

VOTACAO_SECAO = Tabela(
    "votacao_secao",
    (
        *_PARTICAO,
        *_LOCALIZACAO,
        _int("nr_secao", obrigatoria=True),
        _int("cd_cargo", obrigatoria=True),
        _txt("ds_cargo"),
        _int("nr_votavel", obrigatoria=True),
        _txt("nm_votavel"),
        _int("qt_votos", obrigatoria=True),
        _cod("sq_candidato", tipo="BIGINT"),
        _int("nr_local_votacao"),
        _txt("nm_local_votacao"),
        _txt("ds_local_votacao_endereco"),
    ),
)

DETALHE_SECAO = Tabela(
    "detalhe_secao",
    (
        *_PARTICAO,
        *_LOCALIZACAO,
        _int("nr_secao", obrigatoria=True),
        _int("cd_cargo", obrigatoria=True),
        _txt("ds_cargo"),
        _int("qt_aptos", obrigatoria=True),
        _int("qt_comparecimento", obrigatoria=True),
        _int("qt_abstencoes", obrigatoria=True),
        _int("qt_votos_nominais"),
        _int("qt_votos_brancos", obrigatoria=True),
        _int("qt_votos_nulos", obrigatoria=True),
        _int("qt_votos_legenda"),
        _int("qt_votos_anulados_apu_sep"),
        _int("nr_local_votacao"),
        _txt("nm_local_votacao"),
        _txt("ds_local_votacao_endereco"),
    ),
)

# consulta_cand traz NR_CPF_CANDIDATO, DS_EMAIL, DT_NASCIMENTO e
# NR_TITULO_ELEITORAL_CANDIDATO: ficam de fora por não estarem declarados.
CANDIDATOS = Tabela(
    "candidatos",
    (
        *_PARTICAO,
        _txt("sg_uf", obrigatoria=True),
        _int("cd_cargo", obrigatoria=True),
        _txt("ds_cargo"),
        _int("sq_candidato", obrigatoria=True, tipo="BIGINT"),
        _int("nr_candidato", obrigatoria=True),
        _txt("nm_candidato"),
        _txt("nm_urna_candidato"),
        _cod("nr_partido"),
        _txt("sg_partido"),
        _cod("nr_federacao"),
        _txt("sg_federacao"),
        _txt("ds_situacao_candidatura"),
        _txt("ds_genero"),
        _txt("ds_grau_instrucao"),
        _txt("ds_cor_raca"),
        _txt("ds_ocupacao"),
        _txt("ds_sit_tot_turno"),
    ),
)

LOCAIS_VOTACAO = Tabela(
    "locais_votacao",
    (
        *_PARTICAO,
        *_LOCALIZACAO,
        _int("nr_secao", obrigatoria=True),
        _int("nr_local_votacao", obrigatoria=True),
        _txt("nm_local_votacao"),
        _txt("ds_endereco"),
        _txt("nm_bairro"),
        _dbl("nr_latitude"),
        _dbl("nr_longitude"),
        _int("qt_eleitor_secao"),
    ),
)

TABELAS = (
    VOTACAO_MUNZONA,
    DETALHE_MUNZONA,
    VOTACAO_SECAO,
    DETALHE_SECAO,
    CANDIDATOS,
    LOCAIS_VOTACAO,
)
