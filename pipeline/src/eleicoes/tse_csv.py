"""Leitura dos CSVs do TSE com aliasing de colunas (D3).

Cada tabela declara suas colunas de destino com uma lista de nomes de origem
aceitos; vale o primeiro que existir no arquivo. Coluna ausente vira NULL
tipado, ou erro se for obrigatória. O que não está declarado nunca é lido:
é isso que mantém CPF, e-mail etc. fora das camadas derivadas (LGPD).
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

ENCODING = "latin-1"
MARCADORES_NULOS = ("#NULO#", "#NULO", "#NE#", "#NE", "")
CODIGOS_NULOS = ("-1", "-3")  # só em campos de código


class ColunaObrigatoriaAusente(ValueError):
    pass


@dataclass(frozen=True)
class Coluna:
    nome: str
    tipo: str = "VARCHAR"
    aliases: tuple[str, ...] = ()
    obrigatoria: bool = False
    codigo: bool = False

    @property
    def origens(self) -> tuple[str, ...]:
        return self.aliases or (self.nome.upper(),)


@dataclass(frozen=True)
class Tabela:
    nome: str
    colunas: tuple[Coluna, ...]

    def ddl(self, schema: str) -> str:
        cols = ", ".join(f"{c.nome} {c.tipo}" for c in self.colunas)
        return f"CREATE TABLE IF NOT EXISTS {schema}.{self.nome} ({cols})"


def ler_cabecalho(path: Path) -> list[str]:
    with Path(path).open(encoding=ENCODING, newline="") as f:
        return next(csv.reader(f, delimiter=";"))


def resolver(tabela: Tabela, cabecalho: Iterable[str]) -> dict[str, str | None]:
    """Mapeia cada coluna de destino para o nome de origem encontrado (ou None)."""
    existentes = set(cabecalho)
    mapa: dict[str, str | None] = {}
    for col in tabela.colunas:
        origem = next((o for o in col.origens if o in existentes), None)
        if origem is None and col.obrigatoria:
            raise ColunaObrigatoriaAusente(
                f"Tabela {tabela.nome}: coluna obrigatória '{col.nome}' ausente; "
                f"nomes procurados: {', '.join(col.origens)}"
            )
        mapa[col.nome] = origem
    return mapa


def _literal(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def _expr(col: Coluna, origem: str | None) -> str:
    if origem is None:
        return f"CAST(NULL AS {col.tipo}) AS {col.nome}"
    v = f'trim("{origem}")'
    nulos = MARCADORES_NULOS + (CODIGOS_NULOS if col.codigo else ())
    limpo = f"CASE WHEN {v} IN ({', '.join(map(_literal, nulos))}) THEN NULL ELSE {v} END"
    if col.tipo == "VARCHAR":
        return f"{limpo} AS {col.nome}"
    if col.tipo == "DOUBLE":
        return f"CAST(replace({limpo}, ',', '.') AS DOUBLE) AS {col.nome}"
    return f"CAST({limpo} AS {col.tipo}) AS {col.nome}"


def select_sql(tabela: Tabela, arquivos: Sequence[Path]) -> str:
    """SELECT que lê `arquivos` (mesmo dataset) já no schema de `tabela`."""
    if not arquivos:
        raise ValueError(f"Tabela {tabela.nome}: nenhum arquivo para ler")
    cabecalho: list[str] = []
    for arq in arquivos:
        cabecalho += [c for c in ler_cabecalho(arq) if c not in cabecalho]
    mapa = resolver(tabela, cabecalho)
    lista = ", ".join(_literal(str(a)) for a in arquivos)
    exprs = ",\n  ".join(_expr(c, mapa[c.nome]) for c in tabela.colunas)
    return (
        f"SELECT\n  {exprs}\nFROM read_csv([{lista}], delim=';', quote='\"', escape='\"', "
        f"header=true, all_varchar=true, encoding='{ENCODING}', union_by_name=true)"
    )
