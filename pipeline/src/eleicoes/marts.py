"""Modelos analíticos (schema `marts`), reconstruídos do staging completo (D4).

Percentuais (`pct_*`) estão em 0–100, sem arredondamento; `pct_validos` usa
como base os votos válidos (nominais + legenda) do cargo no recorte da linha.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import yaml

from eleicoes.config import CONFIG_DIR

SCHEMA = "marts"
SENADOR = 5
VALIDOS = "tipo_votavel IN ('candidato', 'legenda')"

TABELAS_MARTS = (
    "cargos",
    "resultado_uf",
    "resultado_brasil",
    "comparecimento_uf",
    "itajuba_resultado",
    "itajuba_zona",
    "itajuba_local",
    "itajuba_secao",
    "itajuba_comparecimento",
    "historico_itajuba_partido",
    "historico_itajuba_comparecimento",
)


def _cargos_sql(config: dict) -> str:
    linhas = [
        f"({ano}, {cd}, '{nome}', {config['vagas_senado'][ano] if cd == SENADOR else 1})"
        for ano in config["vagas_senado"]
        for cd, nome in config["cargos"].items()
    ]
    return f"""
CREATE OR REPLACE TABLE {SCHEMA}.cargos AS
SELECT * FROM (VALUES {", ".join(linhas)}) t(ano, cd_cargo, nm_cargo, votos_por_eleitor)"""


RESULTADO_UF = f"""
CREATE OR REPLACE TABLE {SCHEMA}.resultado_uf AS
WITH cand AS (
    SELECT ano, turno, sg_uf, cd_cargo, sq_candidato,
           any_value(nr_candidato) AS nr_candidato,
           any_value(nm_candidato) AS nm_candidato,
           any_value(nm_urna_candidato) AS nm_urna_candidato,
           any_value(nr_partido) AS nr_partido,
           any_value(sg_partido) AS sg_partido,
           any_value(sg_federacao) AS sg_federacao,
           any_value(ds_sit_tot_turno) AS ds_sit_tot_turno,
           sum(coalesce(qt_votos_nominais_validos, qt_votos_nominais))::BIGINT AS votos
    FROM staging.votacao_munzona
    GROUP BY ano, turno, sg_uf, cd_cargo, sq_candidato
), validos AS (
    SELECT ano, turno, sg_uf, cd_cargo,
           sum(coalesce(qt_votos_validos, qt_votos_nominais + coalesce(qt_votos_legenda, 0)))
               ::BIGINT AS votos_validos
    FROM staging.detalhe_munzona
    GROUP BY ALL
)
SELECT ano, turno, sg_uf, cd_cargo, nm_cargo, sq_candidato, nr_candidato, nm_candidato,
       nm_urna_candidato, nr_partido, sg_partido, sg_federacao, ds_sit_tot_turno,
       votos, votos_validos,
       100.0 * votos / nullif(votos_validos, 0) AS pct_validos,
       rank() OVER (PARTITION BY ano, turno, sg_uf, cd_cargo ORDER BY votos DESC) AS posicao
FROM cand
JOIN validos USING (ano, turno, sg_uf, cd_cargo)
JOIN {SCHEMA}.cargos USING (ano, cd_cargo)"""

RESULTADO_BRASIL = f"""
CREATE OR REPLACE TABLE {SCHEMA}.resultado_brasil AS
WITH cand AS (
    SELECT ano, turno, sq_candidato,
           any_value(nr_candidato) AS nr_candidato,
           any_value(nm_candidato) AS nm_candidato,
           any_value(nm_urna_candidato) AS nm_urna_candidato,
           any_value(nr_partido) AS nr_partido,
           any_value(sg_partido) AS sg_partido,
           any_value(sg_federacao) AS sg_federacao,
           any_value(ds_sit_tot_turno) AS ds_sit_tot_turno,
           sum(votos)::BIGINT AS votos
    FROM {SCHEMA}.resultado_uf
    WHERE cd_cargo = 1
    GROUP BY ano, turno, sq_candidato
), validos AS (
    SELECT ano, turno,
           sum(coalesce(qt_votos_validos, qt_votos_nominais + coalesce(qt_votos_legenda, 0)))
               ::BIGINT AS votos_validos
    FROM staging.detalhe_munzona
    WHERE cd_cargo = 1
    GROUP BY ALL
)
SELECT cand.*, votos_validos,
       100.0 * votos / nullif(votos_validos, 0) AS pct_validos,
       rank() OVER (PARTITION BY ano, turno ORDER BY votos DESC) AS posicao
FROM cand JOIN validos USING (ano, turno)"""

COMPARECIMENTO_UF = f"""
CREATE OR REPLACE TABLE {SCHEMA}.comparecimento_uf AS
SELECT *,
       100.0 * comparecimento / nullif(aptos, 0) AS pct_comparecimento,
       100.0 * abstencoes / nullif(aptos, 0) AS pct_abstencao,
       100.0 * brancos / nullif(comparecimento * votos_por_eleitor, 0) AS pct_brancos,
       100.0 * nulos / nullif(comparecimento * votos_por_eleitor, 0) AS pct_nulos
FROM (
    SELECT ano, turno, sg_uf, cd_cargo, nm_cargo, votos_por_eleitor,
           sum(qt_aptos)::BIGINT AS aptos,
           sum(qt_comparecimento)::BIGINT AS comparecimento,
           sum(qt_abstencoes)::BIGINT AS abstencoes,
           sum(coalesce(qt_votos_validos, qt_votos_nominais + coalesce(qt_votos_legenda, 0)))
               ::BIGINT AS votos_validos,
           sum(qt_votos_brancos)::BIGINT AS brancos,
           sum(qt_votos_nulos)::BIGINT AS nulos
    FROM staging.detalhe_munzona
    JOIN {SCHEMA}.cargos USING (ano, cd_cargo)
    GROUP BY ALL
)"""

# Votos por seção de Itajubá, classificados e com partido. 95/96/97 são branco,
# nulo e anulado; sem sq_candidato, o número do votável é o do partido (legenda).
# Candidato ausente da totalização (munzona), como uma candidatura não apta, é
# voto nulo: é assim que o TSE o conta no detalhe por município (caso real de 2026).
ITAJUBA_VOTOS = """
CREATE OR REPLACE TEMP VIEW _itajuba_votos AS
WITH cand AS (
    SELECT ano, turno, sq_candidato,
           any_value(nm_urna_candidato) AS nm_urna_candidato,
           any_value(sg_partido) AS sg_partido
    FROM staging.votacao_munzona
    GROUP BY ALL
), partidos AS (
    SELECT DISTINCT ano, nr_partido, sg_partido FROM staging.votacao_munzona
)
SELECT s.ano, s.turno, s.cd_cargo, s.nr_zona, s.nr_secao, s.nr_local_votacao,
       CASE WHEN s.nr_votavel = 95 THEN 'branco'
            WHEN s.nr_votavel = 96 THEN 'nulo'
            WHEN s.nr_votavel = 97 THEN 'anulado'
            WHEN s.sq_candidato IS NOT NULL AND c.sq_candidato IS NULL THEN 'nulo'
            WHEN s.sq_candidato IS NOT NULL THEN 'candidato'
            ELSE 'legenda' END AS tipo_votavel,
       s.nr_votavel, s.nm_votavel, c.nm_urna_candidato,
       coalesce(c.sg_partido, p.sg_partido) AS sg_partido,
       s.qt_votos
FROM staging.votacao_secao s
LEFT JOIN cand c
       ON c.ano = s.ano AND c.turno = s.turno AND c.sq_candidato = s.sq_candidato
LEFT JOIN partidos p
       ON p.ano = s.ano AND p.nr_partido = s.nr_votavel
      AND s.sq_candidato IS NULL AND s.nr_votavel NOT IN (95, 96, 97)"""


def _itajuba_nivel(alvo: str, chaves: tuple[str, ...]) -> str:
    """Votos de Itajubá agregados por cargo e `chaves`; `alvo` é o destino do CREATE."""
    k = "".join(f", {c}" for c in chaves)
    return f"""
CREATE OR REPLACE {alvo} AS
WITH v AS (
    SELECT ano, turno, cd_cargo{k}, tipo_votavel, nr_votavel,
           any_value(nm_votavel) AS nm_votavel,
           any_value(nm_urna_candidato) AS nm_urna_candidato,
           any_value(sg_partido) AS sg_partido,
           sum(qt_votos)::BIGINT AS votos
    FROM _itajuba_votos
    GROUP BY ALL
)
SELECT ano, turno, cd_cargo, nm_cargo{k}, tipo_votavel, nr_votavel, nm_votavel,
       nm_urna_candidato, sg_partido, votos,
       CASE WHEN {VALIDOS} THEN 100.0 * votos / nullif(
           sum(CASE WHEN {VALIDOS} THEN votos END)
               OVER (PARTITION BY ano, turno, cd_cargo{k}), 0) END AS pct_validos,
       CASE WHEN {VALIDOS} THEN rank() OVER (
           PARTITION BY ano, turno, cd_cargo{k}, {VALIDOS} ORDER BY votos DESC) END AS posicao
FROM v JOIN {SCHEMA}.cargos USING (ano, cd_cargo)"""


ITAJUBA_LOCAL = f"""
CREATE OR REPLACE TABLE {SCHEMA}.itajuba_local AS
WITH nomes AS (
    SELECT ano, turno, nr_zona, nr_local_votacao,
           any_value(nm_local_votacao) AS nm_local_votacao,
           any_value(ds_local_votacao_endereco) AS ds_endereco
    FROM staging.votacao_secao GROUP BY ALL
), coords AS (
    SELECT ano, turno, nr_zona, nr_local_votacao,
           any_value(nm_bairro) AS nm_bairro,
           any_value(nr_latitude) AS nr_latitude,
           any_value(nr_longitude) AS nr_longitude
    FROM staging.locais_votacao GROUP BY ALL
)
SELECT n.*, nomes.nm_local_votacao, nomes.ds_endereco, coords.nm_bairro,
       coords.nr_latitude, coords.nr_longitude
FROM _itajuba_local n
LEFT JOIN nomes USING (ano, turno, nr_zona, nr_local_votacao)
LEFT JOIN coords USING (ano, turno, nr_zona, nr_local_votacao)"""

ITAJUBA_COMPARECIMENTO = f"""
CREATE OR REPLACE TABLE {SCHEMA}.itajuba_comparecimento AS
SELECT ano, turno, cd_cargo, nm_cargo, nr_zona, nr_secao, nr_local_votacao,
       qt_aptos AS aptos, qt_comparecimento AS comparecimento, qt_abstencoes AS abstencoes,
       qt_votos_brancos AS brancos, qt_votos_nulos AS nulos,
       100.0 * qt_comparecimento / nullif(qt_aptos, 0) AS pct_comparecimento
FROM staging.detalhe_secao
JOIN {SCHEMA}.cargos USING (ano, cd_cargo)"""

HISTORICO_PARTIDO = f"""
CREATE OR REPLACE TABLE {SCHEMA}.historico_itajuba_partido AS
SELECT ano, turno, cd_cargo, nm_cargo, sg_partido, votos,
       100.0 * votos / sum(votos) OVER (PARTITION BY ano, turno, cd_cargo) AS pct_validos
FROM (
    SELECT ano, turno, cd_cargo, sg_partido, sum(qt_votos)::BIGINT AS votos
    FROM _itajuba_votos WHERE {VALIDOS} GROUP BY ALL
) JOIN {SCHEMA}.cargos USING (ano, cd_cargo)"""

HISTORICO_COMPARECIMENTO = f"""
CREATE OR REPLACE TABLE {SCHEMA}.historico_itajuba_comparecimento AS
SELECT *, 100.0 * comparecimento / nullif(aptos, 0) AS pct_comparecimento,
       100.0 * abstencoes / nullif(aptos, 0) AS pct_abstencao
FROM (
    SELECT ano, turno, cd_cargo, nm_cargo,
           sum(aptos)::BIGINT AS aptos, sum(comparecimento)::BIGINT AS comparecimento,
           sum(abstencoes)::BIGINT AS abstencoes, sum(brancos)::BIGINT AS brancos,
           sum(nulos)::BIGINT AS nulos
    FROM {SCHEMA}.itajuba_comparecimento GROUP BY ALL
)"""


def carregar_config(path: Path = CONFIG_DIR / "eleicoes.yaml") -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def construir_marts(con: duckdb.DuckDBPyConnection, config: dict | None = None) -> None:
    """Recria todos os marts numa única transação."""
    config = config or carregar_config()
    comandos = [
        f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}",
        _cargos_sql(config),
        RESULTADO_UF,
        RESULTADO_BRASIL,
        COMPARECIMENTO_UF,
        ITAJUBA_VOTOS,
        _itajuba_nivel(f"TABLE {SCHEMA}.itajuba_resultado", ()),
        _itajuba_nivel(f"TABLE {SCHEMA}.itajuba_zona", ("nr_zona",)),
        _itajuba_nivel(
            f"TABLE {SCHEMA}.itajuba_secao", ("nr_zona", "nr_secao", "nr_local_votacao")
        ),
        _itajuba_nivel("TEMP TABLE _itajuba_local", ("nr_zona", "nr_local_votacao")),
        ITAJUBA_LOCAL,
        ITAJUBA_COMPARECIMENTO,
        HISTORICO_PARTIDO,
        HISTORICO_COMPARECIMENTO,
        "DROP TABLE _itajuba_local",
        "DROP VIEW _itajuba_votos",
    ]
    con.execute("BEGIN TRANSACTION")
    try:
        for sql in comandos:
            con.execute(sql)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
