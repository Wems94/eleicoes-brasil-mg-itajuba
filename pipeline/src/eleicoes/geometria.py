"""Malha municipal publicada para o mapa do site (M2).

Parte do TopoJSON do IBGE (qualidade mínima, já quantizado: ~1,4 MB, ~400 KB com
gzip, medido em out/2026) e só troca as propriedades: cada município ganha `id`
(código IBGE), `nome` e `uf`. Os arcos não mudam, então os limites entre
municípios continuam compartilhados e o site deriva deles os limites das UFs.
"""

from __future__ import annotations

import gzip
import json

import duckdb

OBJETO = "municipios"
# Orçamento do arquivo comprimido (o site baixa a malha inteira na visão Brasil).
ORCAMENTO_GZIP = 1_200_000


class MalhaAusente(RuntimeError):
    pass


def montar(con: duckdb.DuckDBPyConnection) -> dict:
    linha = con.execute("SELECT topojson FROM staging.ibge_malha").fetchone()
    if linha is None:
        raise MalhaAusente("staging.ibge_malha vazio: rode o pipeline com as fontes do IBGE")
    topo = json.loads(linha[0])
    nomes = {
        cd: (nome, uf)
        for cd, nome, uf in con.execute(
            "SELECT cd_ibge, nm_municipio, sg_uf FROM staging.ibge_municipios"
        ).fetchall()
    }
    (geometrias,) = [o["geometries"] for o in topo["objects"].values()]
    saida = []
    for g in sorted(geometrias, key=lambda g: int(g["properties"]["codarea"])):
        cd = int(g["properties"]["codarea"])
        nome, uf = nomes.get(cd, (None, None))
        novo = {k: v for k, v in g.items() if k != "properties"}
        saida.append({**novo, "id": cd, "properties": {"nome": nome, "uf": uf}})
    return {
        "type": "Topology",
        "transform": topo["transform"],
        "arcs": topo["arcs"],
        "objects": {OBJETO: {"type": "GeometryCollection", "geometries": saida}},
    }


def serializar(topo: dict) -> bytes:
    """JSON compacto (sem espaços): a malha é o maior arquivo publicado."""
    return json.dumps(topo, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def tamanho_gzip(conteudo: bytes) -> int:
    return len(gzip.compress(conteudo, compresslevel=9, mtime=0))
