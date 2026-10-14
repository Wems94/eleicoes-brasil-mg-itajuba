"""Dados do IBGE no staging: lista oficial de municípios e malha municipal.

As duas tabelas não têm partição (ano, turno): são substituídas inteiras a cada
carga, com a versão do IBGE baixada naquela execução. A malha fica guardada como
o TopoJSON original (texto), para os snapshots dependerem só do banco.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

SCHEMA = "staging"
DDL = (
    f"""CREATE TABLE IF NOT EXISTS {SCHEMA}.ibge_municipios (
        cd_ibge INTEGER, nm_municipio VARCHAR, sg_uf VARCHAR)""",
    f"CREATE TABLE IF NOT EXISTS {SCHEMA}.ibge_malha (topojson VARCHAR)",
)


class MalhaInvalida(ValueError):
    pass


def criar_tabelas(con: duckdb.DuckDBPyConnection) -> None:
    for sql in DDL:
        con.execute(sql)


def ler_municipios(path: Path) -> list[tuple[int, str, str]]:
    """(código IBGE, nome, UF) da API de localidades (`view=nivelado`)."""
    dados = json.loads(Path(path).read_text(encoding="utf-8"))
    return sorted((int(m["municipio-id"]), m["municipio-nome"], m["UF-sigla"]) for m in dados)


def ler_malha(path: Path) -> str:
    """Confere que é um TopoJSON com os municípios identificados por `codarea`."""
    texto = Path(path).read_text(encoding="utf-8")
    topo = json.loads(texto)
    objetos = topo.get("objects") if isinstance(topo, dict) else None
    if topo.get("type") != "Topology" or not objetos:
        raise MalhaInvalida(f"{Path(path).name}: não é um TopoJSON com objetos")
    (geometrias,) = [o["geometries"] for o in objetos.values()]
    if not geometrias or any("codarea" not in g.get("properties", {}) for g in geometrias):
        raise MalhaInvalida(f"{Path(path).name}: geometria sem a propriedade 'codarea'")
    return texto


def carregar(con: duckdb.DuckDBPyConnection, municipios: Path, malha: Path) -> int:
    """Substitui as tabelas do IBGE; devolve o número de municípios da lista."""
    linhas = ler_municipios(municipios)
    topojson = ler_malha(malha)
    con.execute(f"DELETE FROM {SCHEMA}.ibge_municipios")
    con.executemany(f"INSERT INTO {SCHEMA}.ibge_municipios VALUES (?, ?, ?)", linhas)
    con.execute(f"DELETE FROM {SCHEMA}.ibge_malha")
    con.execute(f"INSERT INTO {SCHEMA}.ibge_malha VALUES (?)", [topojson])
    return len(linhas)
