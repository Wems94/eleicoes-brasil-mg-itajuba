"""Gate de qualidade (D6): regras SQL sobre o banco recém-construído.

Cada regra é um SELECT que devolve as linhas violadoras. Regras de severidade
"erro" reprovam o gate (nada é publicado); "aviso" só aparece no relatório.
Roda depois do staging e dos marts, antes de qualquer carga ou publicação.

Uso: python -m eleicoes.qualidade --db data/eleicoes.duckdb --ano 2026 --turno 1
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from eleicoes import esquema
from eleicoes.config import DB_PATH
from eleicoes.marts import carregar_config

EXEMPLOS = 5


@dataclass(frozen=True)
class Regra:
    nome: str
    descricao: str
    sql: str
    severidade: str = "erro"


@dataclass(frozen=True)
class Resultado:
    regra: Regra
    violacoes: int
    exemplos: list[dict] = field(default_factory=list)

    @property
    def falhou(self) -> bool:
        return self.violacoes > 0


@dataclass(frozen=True)
class Relatorio:
    ano: int
    turno: int
    resultados: list[Resultado]

    @property
    def ok(self) -> bool:
        return not any(r.falhou and r.regra.severidade == "erro" for r in self.resultados)

    def texto(self) -> str:
        linhas = [
            f"Gate de qualidade {self.ano}/{self.turno}: {'APROVADO' if self.ok else 'REPROVADO'}"
        ]
        for r in self.resultados:
            if not r.falhou:
                linhas.append(f"  [OK] {r.regra.nome}")
                continue
            marca = "ERRO" if r.regra.severidade == "erro" else "AVISO"
            linhas.append(
                f"  [{marca}] {r.regra.nome}: {r.violacoes} violação(ões) — {r.regra.descricao}"
            )
            linhas += [f"      {e}" for e in r.exemplos]
        return "\n".join(linhas)


class QualidadeReprovada(RuntimeError):
    def __init__(self, relatorio: Relatorio) -> None:
        super().__init__(relatorio.texto())
        self.relatorio = relatorio


# --- regras ----------------------------------------------------------------------

# Chave natural de cada tabela de staging (a partição ano/turno faz parte).
CHAVES = {
    "votacao_munzona": (
        "sg_uf",
        "cd_municipio",
        "nr_zona",
        "cd_cargo",
        "sq_candidato",
        "st_voto_em_transito",
    ),
    "detalhe_munzona": ("sg_uf", "cd_municipio", "nr_zona", "cd_cargo", "st_voto_em_transito"),
    "votacao_secao": ("nr_zona", "nr_secao", "cd_cargo", "nr_votavel"),
    "detalhe_secao": ("nr_zona", "nr_secao", "cd_cargo"),
    "candidatos": ("sq_candidato",),
    "locais_votacao": ("nr_zona", "nr_secao"),
}
TABELAS_DE_VOTOS = ("votacao_munzona", "detalhe_munzona", "votacao_secao", "detalhe_secao")

SOMA_SECAO = """
WITH v AS (
    SELECT ano, turno, nr_zona, nr_secao, cd_cargo, sum(qt_votos) AS votos
    FROM staging.votacao_secao GROUP BY ALL
)
SELECT ano, turno, nr_zona, nr_secao, cd_cargo, d.qt_comparecimento AS comparecimento,
       c.votos_por_eleitor, v.votos, d.qt_comparecimento * c.votos_por_eleitor AS esperado
FROM staging.detalhe_secao d
FULL JOIN v USING (ano, turno, nr_zona, nr_secao, cd_cargo)
LEFT JOIN marts.cargos c USING (ano, cd_cargo)
WHERE coalesce(v.votos, 0)
      IS DISTINCT FROM coalesce(d.qt_comparecimento, 0) * coalesce(c.votos_por_eleitor, 1)
ORDER BY ALL"""

# Verificado com os dados reais de 2026: sem os votos sub judice a soma não fecha.
SOMA_MUNZONA = """
SELECT ano, turno, sg_uf, cd_municipio, nr_zona, cd_cargo, qt_comparecimento,
       votos_por_eleitor, qt_votos_validos, qt_votos_brancos, qt_votos_nulos,
       qt_votos_anulados, qt_votos_anulados_subjudice
FROM staging.detalhe_munzona
JOIN marts.cargos USING (ano, cd_cargo)
WHERE coalesce(qt_votos_validos, qt_votos_nominais + coalesce(qt_votos_legenda, 0))
      + qt_votos_brancos + qt_votos_nulos
      + coalesce(qt_votos_anulados, 0) + coalesce(qt_votos_anulados_subjudice, 0)
      IS DISTINCT FROM qt_comparecimento * votos_por_eleitor
ORDER BY ALL"""

REFERENCIAL_VOTAVEL = """
SELECT DISTINCT s.ano, s.turno, s.cd_cargo, s.nr_votavel, s.nm_votavel, s.sq_candidato
FROM staging.votacao_secao s
WHERE s.sq_candidato IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM staging.votacao_munzona m
                  WHERE (m.ano, m.turno, m.sq_candidato) = (s.ano, s.turno, s.sq_candidato))
  AND NOT EXISTS (SELECT 1 FROM staging.candidatos c
                  WHERE (c.ano, c.sq_candidato) = (s.ano, s.sq_candidato))
ORDER BY ALL"""

FORA_DA_TOTALIZACAO = """
SELECT s.ano, s.turno, s.cd_cargo, s.nr_votavel, any_value(s.nm_votavel) AS nm_votavel,
       s.sq_candidato, sum(s.qt_votos) AS votos
FROM staging.votacao_secao s
WHERE s.sq_candidato IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM staging.votacao_munzona m
                  WHERE (m.ano, m.turno, m.sq_candidato) = (s.ano, s.turno, s.sq_candidato))
GROUP BY s.ano, s.turno, s.cd_cargo, s.nr_votavel, s.sq_candidato
ORDER BY ALL"""

PERCENTUAIS = """
SELECT 'resultado_uf' AS mart, ano, turno, sg_uf, cd_cargo, sum(pct_validos) AS soma_pct
FROM marts.resultado_uf WHERE cd_cargo IN (1, 3, 5)
GROUP BY ALL HAVING abs(sum(pct_validos) - 100) > 1e-6
UNION ALL
SELECT 'resultado_brasil', ano, turno, 'BR', 1, sum(pct_validos)
FROM marts.resultado_brasil
GROUP BY ALL HAVING abs(sum(pct_validos) - 100) > 1e-6
ORDER BY ALL"""


def _lista(valores: Sequence[object]) -> str:
    return ", ".join(f"'{v}'" if isinstance(v, str) else str(v) for v in valores)


def regras(ano: int, turno: int, ufs: Sequence[str], cargos: Sequence[int]) -> list[Regra]:
    for uf in ufs:
        if not re.fullmatch(r"[A-Z]{2}", uf):
            raise ValueError(f"UF inválida: {uf!r}")
    out = [
        Regra(
            "soma_secao_itajuba",
            "votos da seção ≠ comparecimento × votos por eleitor",
            SOMA_SECAO,
        ),
        Regra(
            "soma_munzona",
            "válidos + brancos + nulos + anulados + sub judice"
            " ≠ comparecimento × votos por eleitor",
            SOMA_MUNZONA,
        ),
    ]
    for tabela, chave in CHAVES.items():
        k = ", ".join(("ano", "turno", *chave))
        out.append(
            Regra(
                f"unicidade_{tabela}",
                f"chave ({k}) duplicada em staging.{tabela}",
                f"SELECT {k}, count(*) AS n FROM staging.{tabela} "
                f"GROUP BY {k} HAVING count(*) > 1 ORDER BY ALL",
            )
        )
    out.append(
        Regra(
            "dominio_cargo",
            f"cd_cargo fora de ({_lista(cargos)})",
            " UNION ALL ".join(
                f"SELECT '{t}' AS tabela, ano, turno, cd_cargo, count(*) AS n FROM staging.{t} "
                f"WHERE cd_cargo NOT IN ({_lista(cargos)}) GROUP BY ALL"
                for t in TABELAS_DE_VOTOS
            ),
        )
    )
    negativos = [
        f"SELECT '{t.nome}' AS tabela, '{c.nome}' AS coluna, ano, turno, count(*) AS n "
        f"FROM staging.{t.nome} WHERE {c.nome} < 0 GROUP BY ALL"
        for t in esquema.TABELAS
        for c in t.colunas
        if c.nome.startswith("qt_")
    ]
    out += [
        Regra("votos_nao_negativos", "quantidade negativa", " UNION ALL ".join(negativos)),
        Regra(
            "referencial_votavel",
            "votável nominal sem candidato no munzona nem no consulta_cand",
            REFERENCIAL_VOTAVEL,
        ),
        Regra(
            "votavel_fora_da_totalizacao",
            "candidato na seção mas não no munzona (contado como nulo, como faz o TSE)",
            FORA_DA_TOTALIZACAO,
            severidade="aviso",
        ),
        Regra(
            "completude_ufs",
            "UF sem dados no 1º turno",
            # No 2º turno só há as UFs com disputa: não dá para exigir todas.
            f"""SELECT sg_uf FROM (VALUES {", ".join(f"('{u}')" for u in ufs)}) t(sg_uf)
                WHERE {turno} = 1 AND sg_uf NOT IN (
                    SELECT sg_uf FROM staging.detalhe_munzona WHERE ano = {ano} AND turno = {turno}
                    INTERSECT
                    SELECT sg_uf FROM staging.votacao_munzona WHERE ano = {ano} AND turno = {turno})
                ORDER BY 1""",
        ),
        Regra(
            "completude_itajuba",
            "cargo votado em MG sem dados por seção de Itajubá",
            f"""WITH mg AS (
                    SELECT DISTINCT cd_cargo FROM staging.detalhe_munzona
                    WHERE ano = {ano} AND turno = {turno} AND sg_uf = 'MG')
                SELECT t.tabela, mg.cd_cargo
                FROM mg, (VALUES ('votacao_secao'), ('detalhe_secao')) t(tabela)
                WHERE NOT EXISTS (
                    SELECT 1 FROM staging.votacao_secao s
                    WHERE t.tabela = 'votacao_secao'
                      AND (s.ano, s.turno, s.cd_cargo) = ({ano}, {turno}, mg.cd_cargo))
                  AND NOT EXISTS (
                    SELECT 1 FROM staging.detalhe_secao s
                    WHERE t.tabela = 'detalhe_secao'
                      AND (s.ano, s.turno, s.cd_cargo) = ({ano}, {turno}, mg.cd_cargo))
                ORDER BY ALL""",
        ),
        Regra(
            "percentuais_validos",
            "percentuais dos majoritários não somam 100%",
            PERCENTUAIS,
        ),
    ]
    return out


def executar(
    con: duckdb.DuckDBPyConnection,
    ano: int,
    turno: int,
    *,
    ufs: Sequence[str] | None = None,
    config: dict | None = None,
) -> Relatorio:
    config = config or carregar_config()
    ufs = tuple(ufs or config["ufs"])
    resultados = []
    for regra in regras(ano, turno, ufs, tuple(config["cargos"])):
        (n,) = con.execute(f"SELECT count(*) FROM ({regra.sql})").fetchone()
        exemplos = []
        if n:
            rel = con.sql(f"SELECT * FROM ({regra.sql}) LIMIT {EXEMPLOS}")
            exemplos = [dict(zip(rel.columns, linha, strict=True)) for linha in rel.fetchall()]
        resultados.append(Resultado(regra, n, exemplos))
    return Relatorio(ano, turno, resultados)


def gate(con: duckdb.DuckDBPyConnection, ano: int, turno: int, **kwargs) -> Relatorio:
    """Executa as regras e levanta `QualidadeReprovada` se alguma de erro falhar."""
    relatorio = executar(con, ano, turno, **kwargs)
    if not relatorio.ok:
        raise QualidadeReprovada(relatorio)
    return relatorio


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Gate de qualidade do banco de eleições")
    p.add_argument("--db", type=Path, default=DB_PATH)
    p.add_argument("--ano", type=int, required=True)
    p.add_argument("--turno", type=int, required=True)
    p.add_argument("--ufs", nargs="+", help="UFs esperadas (padrão: config/eleicoes.yaml)")
    args = p.parse_args(argv)
    con = duckdb.connect(str(args.db), read_only=True)
    try:
        relatorio = executar(con, args.ano, args.turno, ufs=args.ufs)
    finally:
        con.close()
    print(relatorio.texto())
    return 0 if relatorio.ok else 1


if __name__ == "__main__":
    sys.exit(main())
