"""Verificador LGPD: falha se dados pessoais de candidatos aparecerem no banco
derivado ou nos snapshots publicados.

Procura (1) colunas/chaves com nomes proibidos e (2) valores com padrão de CPF
(com dígitos verificadores válidos, para evitar falso positivo) ou de e-mail.
O relatório mascara o que encontra: logs de CI de repositório público são públicos.

Uso: python -m eleicoes.lgpd --db data/eleicoes.duckdb --snapshots ../web/data
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import duckdb

NOME_PROIBIDO = re.compile(r"cpf|e_?mail|nascimento|titulo_eleitoral", re.IGNORECASE)
CPF_TEXTO = r"(^|[^0-9])[0-9]{3}\.?[0-9]{3}\.?[0-9]{3}-?[0-9]{2}([^0-9]|$)"
EMAIL = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"
_CPF_EM_TEXTO = re.compile(r"(?<![0-9])([0-9]{3}\.?[0-9]{3}\.?[0-9]{3}-?[0-9]{2})(?![0-9])")
_EMAIL = re.compile(EMAIL)
SCHEMAS_DO_SISTEMA = ("information_schema", "pg_catalog")
# CPF guardado como número: só 10–11 dígitos. Contagens eleitorais (aptos ~155 mi)
# nunca chegam a 1 bilhão; 9 dígitos daria falso positivo em 1% dos totais nacionais.
# Custo: CPF iniciado por 0 gravado como número escapa (em texto, não escapa).
CPF_NUM_MIN, CPF_NUM_MAX = 1_000_000_000, 99_999_999_999


@dataclass(frozen=True)
class Vazamento:
    local: str
    tipo: str  # "coluna proibida" | "cpf" | "email"
    exemplo: str = ""

    def __str__(self) -> str:
        return f"{self.tipo}: {self.local}" + (f" ({self.exemplo})" if self.exemplo else "")


def cpf_valido(valor: str | int) -> bool:
    d = re.sub(r"\D", "", str(valor))
    if len(d) != 11 or len(set(d)) == 1:
        return False
    for n in (9, 10):
        s = sum(int(d[i]) * (n + 1 - i) for i in range(n)) % 11
        if int(d[n]) != (0 if s < 2 else 11 - s):
            return False
    return True


def mascarar(tipo: str, valor: str) -> str:
    if tipo == "cpf":
        d = re.sub(r"\D", "", valor)
        return f"{d[:3]}.***.***-{d[-2:]}"
    if tipo == "email":
        usuario, _, dominio = valor.partition("@")
        return f"{usuario[:1]}***@{dominio}"
    return ""


def _achados_em_texto(texto: str) -> Iterator[tuple[str, str]]:
    for m in _CPF_EM_TEXTO.finditer(texto):
        if cpf_valido(m.group(1)):
            yield "cpf", mascarar("cpf", m.group(1))
    for m in _EMAIL.finditer(texto):
        yield "email", mascarar("email", m.group(0))


# --- banco -----------------------------------------------------------------------


def verificar_banco(con: duckdb.DuckDBPyConnection, *, exemplos: int = 3) -> list[Vazamento]:
    colunas = con.execute(
        f"""SELECT table_schema, table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema NOT IN {SCHEMAS_DO_SISTEMA} AND table_catalog = current_database()
            ORDER BY ALL"""
    ).fetchall()
    out: list[Vazamento] = []
    for schema, tabela, coluna, tipo in colunas:
        local = f"{schema}.{tabela}.{coluna}"
        ref = f'"{schema}"."{tabela}"'
        col = f'"{coluna}"'
        if NOME_PROIBIDO.search(coluna):
            out.append(Vazamento(local, "coluna proibida"))
        if tipo == "VARCHAR":
            # Pré-filtro em SQL; a validação do DV (que elimina falso positivo) é em Python.
            suspeitos = con.execute(
                f"""SELECT DISTINCT {col} FROM {ref}
                    WHERE regexp_matches({col}, '{CPF_TEXTO}')
                       OR regexp_matches({col}, '{EMAIL}')"""
            ).fetchall()
            achados = {a for (v,) in suspeitos for a in _achados_em_texto(v)}
            for t in ("cpf", "email"):
                ex = sorted(m for tp, m in achados if tp == t)[:exemplos]
                if ex:
                    out.append(Vazamento(local, t, ", ".join(ex)))
        elif tipo in ("BIGINT", "HUGEINT", "UBIGINT"):
            suspeitos = con.execute(
                f"SELECT DISTINCT {col} FROM {ref} WHERE {col} BETWEEN ? AND ?",
                [CPF_NUM_MIN, CPF_NUM_MAX],
            ).fetchall()
            cpfs = sorted(
                mascarar("cpf", f"{v:011d}") for (v,) in suspeitos if cpf_valido(f"{v:011d}")
            )
            if cpfs:
                out.append(Vazamento(local, "cpf", ", ".join(cpfs[:exemplos])))
    return out


# --- snapshots ---------------------------------------------------------------------


def _percorrer(valor: object, caminho: str) -> Iterator[tuple[str, str, str]]:
    if isinstance(valor, dict):
        for k, v in valor.items():
            filho = f"{caminho}.{k}"
            if NOME_PROIBIDO.search(str(k)):
                yield filho, "coluna proibida", ""
            yield from _percorrer(v, filho)
    elif isinstance(valor, list):
        for i, v in enumerate(valor):
            yield from _percorrer(v, f"{caminho}[{i}]")
    elif isinstance(valor, str):
        for tipo, ex in _achados_em_texto(valor):
            yield caminho, tipo, ex
    elif (
        isinstance(valor, int)
        and not isinstance(valor, bool)
        and CPF_NUM_MIN <= valor <= CPF_NUM_MAX
        and cpf_valido(f"{valor:011d}")
    ):
        yield caminho, "cpf", mascarar("cpf", f"{valor:011d}")


def verificar_snapshots(diretorio: Path) -> list[Vazamento]:
    diretorio = Path(diretorio)
    if not diretorio.exists():
        return []
    out = []
    for arq in sorted(diretorio.rglob("*.json")):
        rel = arq.relative_to(diretorio).as_posix()
        dados = json.loads(arq.read_text(encoding="utf-8"))
        out += [Vazamento(f"{rel}:{c}", t, ex) for c, t, ex in _percorrer(dados, "$")]
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Verificador LGPD do banco e dos snapshots")
    p.add_argument("--db", type=Path, help="banco DuckDB a verificar")
    p.add_argument("--snapshots", type=Path, action="append", default=[], help="diretório JSON")
    args = p.parse_args(argv)
    if not args.db and not args.snapshots:
        p.error("informe --db e/ou --snapshots")

    vazamentos: list[Vazamento] = []
    if args.db:
        con = duckdb.connect(str(args.db), read_only=True)
        try:
            vazamentos += verificar_banco(con)
        finally:
            con.close()
    for d in args.snapshots:
        vazamentos += verificar_snapshots(d)

    if vazamentos:
        print(f"LGPD: {len(vazamentos)} vazamento(s) encontrado(s)")
        for v in vazamentos:
            print(f"  [ERRO] {v}")
        return 1
    print("LGPD: nenhum dado pessoal encontrado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
