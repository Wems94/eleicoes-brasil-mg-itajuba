"""Snapshots JSON que alimentam o site estático (D7, D8).

Tudo é gravado num diretório temporário ao lado do destino e só então trocado
por renomeação: uma falha no meio deixa o diretório publicado intacto. A saída
é determinística (mesmos dados -> mesmos bytes, exceto `gerado_em`), para que o
PR de snapshots mostre só o que mudou.

Contrato (schema_versao 2), relativo ao diretório publicado:
  manifest.json                    anos/turnos, origens (sha256), sha256 de cada arquivo
  historico_itajuba.json           todos os anos: partido × cargo majoritário, comparecimento
  geo/municipios.topo.json         malha municipal do IBGE (id = código IBGE, nome, uf)
  fotos/{ano}/{sq}.jpg             fotos dos candidatos a Presidente (160×200)
  {ano}/{turno}/brasil.json        Presidente nacional (com `foto`) + vencedor por UF
  {ano}/{turno}/uf/{UF}.json       todos os cargos da UF + comparecimento
  {ano}/{turno}/mapa/{cargo}.json  camada do mapa: vencedor e abstenção por município e UF
  {ano}/{turno}/municipios/{UF}/{cargo}.json  detalhe por município e zona (sob demanda)
  {ano}/{turno}/itajuba.json       Itajubá por cargo, zona e local de votação
  {ano}/{turno}/itajuba_secoes.json  Itajubá por seção (formato compacto)

`{cargo}` é um slug (CARGOS_MAPA); `deputado-estadual` inclui o Distrital do DF.
Nos cargos proporcionais o mapa é por partido (nominais + legenda).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from eleicoes import geometria

SCHEMA_VERSAO = 2
FONTE = "TSE — Portal de Dados Abertos (dadosabertos.tse.jus.br)"
MAJORITARIOS = (1, 3, 5)
TOP_LOCAL_PROPORCIONAIS = 10  # por local de votação, só os 10 mais votados de deputado
TOP_CANDIDATOS_MAPA = 10  # no detalhe por município/zona dos proporcionais
# slug do mapa -> (nome, códigos de cargo do TSE, camada por partido?)
CARGOS_MAPA: dict[str, tuple[str, tuple[int, ...], bool]] = {
    "presidente": ("Presidente", (1,), False),
    "governador": ("Governador", (3,), False),
    "senador": ("Senador", (5,), False),
    "deputado-federal": ("Deputado Federal", (6,), True),
    "deputado-estadual": ("Deputado Estadual", (7, 8), True),
}


def _linhas(con: duckdb.DuckDBPyConnection, sql: str, params: list | None = None) -> list[dict]:
    rel = con.execute(sql, params or [])
    nomes = [d[0] for d in rel.description]
    return [dict(zip(nomes, linha, strict=True)) for linha in rel.fetchall()]


def _pct(v: float | None) -> float | None:
    return None if v is None else round(v, 2)


def _candidato(r: dict) -> dict:
    return {
        "numero": r["nr_candidato"],
        "nome": r["nm_urna_candidato"],
        "partido": r["sg_partido"],
        "federacao": r["sg_federacao"],
        "votos": r["votos"],
        "pct": _pct(r["pct_validos"]),
        "situacao": r["ds_sit_tot_turno"],
        "posicao": r["posicao"],
    }


def _comparecimento(r: dict) -> dict:
    out = {k: r[k] for k in ("aptos", "comparecimento", "abstencoes", "brancos", "nulos") if k in r}
    for k in ("pct_comparecimento", "pct_abstencao", "pct_brancos", "pct_nulos"):
        if k in r:
            out[k] = _pct(r[k])
    return out


# --- arquivos por (ano, turno) ---------------------------------------------------------


def _foto(ano: int, sq: int) -> str:
    return f"fotos/{ano}/{sq}.jpg"


def _brasil(
    con: duckdb.DuckDBPyConnection, ano: int, turno: int, fotos: set[tuple[int, int]]
) -> dict:
    cands = _linhas(
        con,
        """SELECT * FROM marts.resultado_brasil WHERE ano = ? AND turno = ?
           ORDER BY posicao, nr_candidato""",
        [ano, turno],
    )
    vencedores = _linhas(
        con,
        """SELECT r.sg_uf, r.nr_candidato, r.nm_urna_candidato, r.sg_partido, r.pct_validos,
                  c.pct_comparecimento
           FROM marts.resultado_uf r
           JOIN marts.comparecimento_uf c USING (ano, turno, sg_uf, cd_cargo)
           WHERE r.ano = ? AND r.turno = ? AND r.cd_cargo = 1 AND r.posicao = 1
           ORDER BY r.sg_uf, r.nr_candidato""",
        [ano, turno],
    )
    (total,) = _linhas(
        con,
        """SELECT sum(aptos) AS aptos, sum(comparecimento) AS comparecimento,
                  sum(abstencoes) AS abstencoes, sum(brancos) AS brancos, sum(nulos) AS nulos,
                  100.0 * sum(comparecimento) / nullif(sum(aptos), 0) AS pct_comparecimento,
                  100.0 * sum(abstencoes) / nullif(sum(aptos), 0) AS pct_abstencao,
                  100.0 * sum(brancos) / nullif(sum(comparecimento), 0) AS pct_brancos,
                  100.0 * sum(nulos) / nullif(sum(comparecimento), 0) AS pct_nulos
           FROM marts.comparecimento_uf WHERE ano = ? AND turno = ? AND cd_cargo = 1""",
        [ano, turno],
    )
    return {
        "ano": ano,
        "turno": turno,
        "presidente": (
            {
                "votos_validos": cands[0]["votos_validos"],
                "candidatos": [
                    {
                        **_candidato(c),
                        "foto": _foto(ano, c["sq_candidato"])
                        if (ano, c["sq_candidato"]) in fotos
                        else None,
                    }
                    for c in cands
                ],
            }
            if cands
            else None
        ),
        "comparecimento": _comparecimento(total) if total["aptos"] else None,
        "ufs": [
            {
                "uf": v["sg_uf"],
                "vencedor": {
                    "numero": v["nr_candidato"],
                    "nome": v["nm_urna_candidato"],
                    "partido": v["sg_partido"],
                    "pct": _pct(v["pct_validos"]),
                },
                "pct_comparecimento": _pct(v["pct_comparecimento"]),
            }
            for v in vencedores
        ],
    }


def _uf(con: duckdb.DuckDBPyConnection, ano: int, turno: int, uf: str) -> dict:
    linhas = _linhas(
        con,
        """SELECT * FROM marts.resultado_uf WHERE ano = ? AND turno = ? AND sg_uf = ?
           ORDER BY cd_cargo, posicao, nr_candidato""",
        [ano, turno, uf],
    )
    cargos: dict[int, dict] = {}
    for r in linhas:
        cargo = cargos.setdefault(
            r["cd_cargo"],
            {
                "codigo": r["cd_cargo"],
                "nome": r["nm_cargo"],
                "votos_validos": r["votos_validos"],
                "candidatos": [],
            },
        )
        cargo["candidatos"].append(_candidato(r))
    comparecimento = _linhas(
        con,
        """SELECT * FROM marts.comparecimento_uf WHERE ano = ? AND turno = ? AND sg_uf = ?
           ORDER BY cd_cargo""",
        [ano, turno, uf],
    )
    return {
        "ano": ano,
        "turno": turno,
        "uf": uf,
        "cargos": list(cargos.values()),
        "comparecimento": [
            {"codigo": c["cd_cargo"], "nome": c["nm_cargo"], **_comparecimento(c)}
            for c in comparecimento
        ],
    }


# --- mapa municipal ---------------------------------------------------------------------


def _cem(v: float | None) -> int | None:
    """Percentual 0–100 como inteiro em centésimos (62,37% -> 6237): arquivo menor."""
    return None if v is None else round(v * 100)


def _cargos_sql(codigos: tuple[int, ...]) -> str:
    return "(" + ", ".join(map(str, codigos)) + ")"


def _vencedores(linhas: list[dict], chave: str) -> dict[tuple, dict]:
    """Agrupa por `chave` e devolve o 1º colocado, ou None se houver empate."""
    por: dict[tuple, list[dict]] = {}
    for r in linhas:
        por.setdefault(tuple(r[k] for k in chave.split(",")), []).append(r)
    out = {}
    for k, rs in por.items():
        primeiros = [r for r in rs if r["posicao"] == 1]
        out[k] = primeiros[0] if len(primeiros) == 1 else {**primeiros[0], "empate": True}
    return out


def _mapa_linhas(
    con: duckdb.DuckDBPyConnection, ano: int, turno: int, slug: str, nivel: str
) -> list[dict]:
    """1º colocado (e empatados) por município ou UF, com a abstenção do cargo."""
    _, codigos, por_partido = CARGOS_MAPA[slug]
    p = [ano, turno]
    if nivel == "municipio":
        chave, junta = "sg_uf, cd_municipio", "USING (ano, turno, sg_uf, cd_municipio, cd_cargo)"
        votos = "marts.partido_municipio" if por_partido else "marts.resultado_municipio"
        comp = "marts.comparecimento_municipio"
    elif por_partido:  # partido por UF: soma dos municípios (não há mart por UF)
        return _linhas(
            con,
            f"""WITH p AS (
                    SELECT sg_uf, cd_cargo, sg_partido, nr_partido, sum(votos) AS votos
                    FROM marts.partido_municipio
                    WHERE ano = ? AND turno = ? AND cd_cargo IN {_cargos_sql(codigos)}
                    GROUP BY ALL)
                SELECT p.*, 100.0 * p.votos / nullif(c.votos_validos, 0) AS pct_validos,
                       rank() OVER (PARTITION BY p.sg_uf, p.cd_cargo ORDER BY p.votos DESC)
                           AS posicao,
                       c.pct_abstencao, NULL AS sq_candidato, NULL AS nr_candidato,
                       NULL AS nm_urna_candidato
                FROM p JOIN marts.comparecimento_uf c
                     ON (c.ano, c.turno, c.sg_uf, c.cd_cargo) = (?, ?, p.sg_uf, p.cd_cargo)
                QUALIFY posicao = 1 ORDER BY ALL""",
            [*p, *p],
        )
    else:
        chave, junta = "sg_uf", "USING (ano, turno, sg_uf, cd_cargo)"
        votos, comp = "marts.resultado_uf", "marts.comparecimento_uf"
    cand = "" if por_partido else ", r.sq_candidato, r.nr_candidato, r.nm_urna_candidato"
    return _linhas(
        con,
        f"""SELECT {", ".join(f"r.{k.strip()}" for k in chave.split(","))}, r.cd_cargo,
                   r.sg_partido, r.nr_partido, r.votos, r.pct_validos, r.posicao,
                   c.pct_abstencao{cand}
            FROM {votos} r JOIN {comp} c {junta}
            WHERE r.ano = ? AND r.turno = ? AND r.cd_cargo IN {_cargos_sql(codigos)}
              AND r.posicao = 1
            ORDER BY ALL""",
        p,
    )


def _mapa(
    con: duckdb.DuckDBPyConnection,
    ano: int,
    turno: int,
    slug: str,
    ibge: dict[tuple, int],
    sem_poligono: dict[int, dict] | None = None,
) -> dict:
    nome, _, por_partido = CARGOS_MAPA[slug]
    votaveis: list[dict] = []
    indice: dict[str, int] = {}

    def entrada(r: dict) -> list:
        if r.get("empate"):
            idx = -1
        else:
            k = r["sg_partido"] if por_partido else str(r["sq_candidato"])
            if k not in indice:
                indice[k] = len(votaveis)
                votaveis.append(
                    {
                        "chave": k,
                        "numero": r["nr_partido"],
                        "nome": r["sg_partido"],
                        "partido": r["sg_partido"],
                    }
                    if por_partido
                    else {
                        "chave": k,
                        "numero": r["nr_candidato"],
                        "nome": r["nm_urna_candidato"],
                        "partido": r["sg_partido"],
                    }
                )
            idx = indice[k]
        return [idx, _cem(r["pct_validos"]), _cem(r["pct_abstencao"])]

    chave_mun = "sg_uf,cd_municipio"
    municipios = {}
    for (uf, cd), r in sorted(
        _vencedores(_mapa_linhas(con, ano, turno, slug, "municipio"), chave_mun).items()
    ):
        if uf == "ZZ" or (uf, cd) not in ibge:
            continue
        municipios[str(ibge[(uf, cd)])] = entrada(r)
    ufs = _vencedores(_mapa_linhas(con, ano, turno, slug, "uf"), "sg_uf")
    exterior = ufs.pop(("ZZ",), None)
    return {
        "ano": ano,
        "turno": turno,
        "cargo": slug,
        "nome": nome,
        "por": "partido" if por_partido else "candidato",
        "votaveis": votaveis,
        # código IBGE -> [índice do vencedor (-1 = empate), pct×100, abstenção×100]
        "municipios": dict(sorted(municipios.items())),
        "ufs": {uf: entrada(r) for (uf,), r in sorted(ufs.items())},
        "exterior": entrada(exterior) if exterior else None,
        # municípios com dados mas sem polígono na malha (ex.: criados depois dela)
        "sem_geometria": {
            str(cd): info
            for cd, info in sorted((sem_poligono or {}).items())
            if str(cd) in municipios
        },
    }


def _detalhe_uf(
    con: duckdb.DuckDBPyConnection,
    ano: int,
    turno: int,
    uf: str,
    slug: str,
    ibge: dict[tuple, int],
    nomes_ibge: dict[int, str],
) -> dict:
    """Município e zonas de uma UF para um cargo: o painel do mapa."""
    _, codigos, por_partido = CARGOS_MAPA[slug]
    p = [ano, turno, uf]
    filtro = f"ano = ? AND turno = ? AND sg_uf = ? AND cd_cargo IN {_cargos_sql(codigos)}"
    votaveis: dict[str, dict] = {}

    def votos_de(linhas: list[dict], partido: bool) -> dict[tuple, list]:
        grupos: dict[tuple, list] = {}
        for r in linhas:
            k = r["sg_partido"] if partido else str(r["sq_candidato"])
            if k not in votaveis:
                votaveis[k] = (
                    {"numero": r["nr_partido"], "nome": r["sg_partido"], "partido": r["sg_partido"]}
                    if partido
                    else {
                        "numero": r["nr_candidato"],
                        "nome": r["nm_urna_candidato"],
                        "partido": r["sg_partido"],
                    }
                )
            grupos.setdefault((r["cd_municipio"], r.get("nr_zona")), []).append(
                [k, r["votos"], _pct(r["pct_validos"])]
            )
        return grupos

    def consulta(tabela: str, zona: bool, extra: str = "") -> list[dict]:
        z = ", nr_zona" if zona else ""
        return _linhas(
            con,
            f"""SELECT * {", NULL AS nr_zona" if not zona else ""} FROM {tabela}
                WHERE {filtro} {extra}
                ORDER BY cd_municipio{z}, votos DESC, {
                "sg_partido" if "partido" in tabela else "nr_candidato"
            }""",
            p,
        )

    top = f"AND posicao <= {TOP_CANDIDATOS_MAPA}"
    if por_partido:
        principal = {
            **votos_de(consulta("marts.partido_municipio", False), True),
            **votos_de(consulta("marts.partido_zona", True), True),
        }
        candidatos = {
            **votos_de(consulta("marts.resultado_municipio", False, top), False),
            **votos_de(consulta("marts.resultado_zona", True, top), False),
        }
    else:
        principal = {
            **votos_de(consulta("marts.resultado_municipio", False), False),
            **votos_de(consulta("marts.resultado_zona", True), False),
        }
        candidatos = {}

    comparecimento: dict[tuple, dict] = {}
    for tabela, zona in (
        ("marts.comparecimento_municipio", False),
        ("marts.comparecimento_zona", True),
    ):
        for r in _linhas(con, f"SELECT * FROM {tabela} WHERE {filtro} ORDER BY ALL", p):
            comparecimento[(r["cd_municipio"], r["nr_zona"] if zona else None)] = _comparecimento(r)
    # municípios atendidos por cada zona (uma zona pode atender vários)
    por_zona: dict[int, int] = {}
    for _cd, z in comparecimento:
        if z is not None:
            por_zona[z] = por_zona.get(z, 0) + 1

    def bloco(cd: int, z: int | None) -> dict:
        b = {"comparecimento": comparecimento.get((cd, z)), "votos": principal.get((cd, z), [])}
        if por_partido:
            b["candidatos"] = candidatos.get((cd, z), [])
        return b

    municipios = {}
    tse = sorted({cd for cd, _z in comparecimento})
    for cd in tse:
        cd_ibge = ibge.get((uf, cd))
        if cd_ibge is None:
            continue
        zonas = sorted(z for c, z in comparecimento if c == cd and z is not None)
        municipios[str(cd_ibge)] = {
            "nome": nomes_ibge.get(cd_ibge),
            "codigo_tse": cd,
            "total": bloco(cd, None),
            "zonas": [
                {"zona": z, "outros_municipios": por_zona[z] - 1, **bloco(cd, z)} for z in zonas
            ],
        }
    return {
        "ano": ano,
        "turno": turno,
        "uf": uf,
        "cargo": slug,
        "por": "partido" if por_partido else "candidato",
        "votaveis": dict(sorted(votaveis.items())),
        "municipios": dict(sorted(municipios.items())),
    }


def _votavel(r: dict) -> dict:
    return {
        "tipo": r["tipo_votavel"],
        "numero": r["nr_votavel"],
        "nome": r["nm_urna_candidato"] or r["nm_votavel"],
        "partido": r["sg_partido"],
        "votos": r["votos"],
        "pct": _pct(r["pct_validos"]),
        "posicao": r["posicao"],
    }


def _ordem(*antes: str) -> str:
    """Candidatos e legendas primeiro (por votos), depois brancos, nulos e anulados."""
    criterio = "CASE WHEN tipo_votavel IN ('candidato', 'legenda') THEN 0 ELSE 1 END"
    return "ORDER BY " + ", ".join([*antes, criterio, "votos DESC", "nr_votavel"])


def _por_cargo(linhas: list[dict], chave: tuple[str, ...] = ()) -> dict[tuple, dict[int, list]]:
    grupos: dict[tuple, dict[int, list]] = {}
    for r in linhas:
        grupos.setdefault(tuple(r[k] for k in chave), {}).setdefault(r["cd_cargo"], []).append(
            _votavel(r)
        )
    return grupos


def _itajuba(con: duckdb.DuckDBPyConnection, ano: int, turno: int) -> dict:
    p = [ano, turno]
    comparecimento = {
        c["cd_cargo"]: c
        for c in _linhas(
            con,
            "SELECT * FROM marts.historico_itajuba_comparecimento WHERE ano = ? AND turno = ?",
            p,
        )
    }
    nomes_cargo = {
        r["cd_cargo"]: r["nm_cargo"]
        for r in _linhas(con, "SELECT cd_cargo, nm_cargo FROM marts.cargos WHERE ano = ?", [ano])
    }
    por_cargo = _por_cargo(
        _linhas(
            con,
            f"SELECT * FROM marts.itajuba_resultado WHERE ano = ? AND turno = ? "
            f"{_ordem('cd_cargo')}",
            p,
        )
    ).get((), {})
    zonas = _por_cargo(
        _linhas(
            con,
            f"SELECT * FROM marts.itajuba_zona WHERE ano = ? AND turno = ? "
            f"{_ordem('nr_zona', 'cd_cargo')}",
            p,
        ),
        ("nr_zona",),
    )
    locais_votos = _por_cargo(
        _linhas(
            con,
            f"""SELECT * FROM marts.itajuba_local WHERE ano = ? AND turno = ?
                AND (cd_cargo IN {MAJORITARIOS} OR tipo_votavel NOT IN ('candidato', 'legenda')
                     OR posicao <= {TOP_LOCAL_PROPORCIONAIS})
                {_ordem("nr_zona", "nr_local_votacao", "cd_cargo")}""",
            p,
        ),
        ("nr_zona", "nr_local_votacao"),
    )
    locais = _linhas(
        con,
        """SELECT l.nr_zona, l.nr_local_votacao,
                  any_value(l.nm_local_votacao) AS nome, any_value(l.ds_endereco) AS endereco,
                  any_value(l.nm_bairro) AS bairro, any_value(l.nr_latitude) AS lat,
                  any_value(l.nr_longitude) AS lon,
                  (SELECT list(DISTINCT c.nr_secao ORDER BY c.nr_secao)
                   FROM marts.itajuba_comparecimento c
                   WHERE (c.ano, c.turno, c.nr_zona, c.nr_local_votacao)
                       = (l.ano, l.turno, l.nr_zona, l.nr_local_votacao)) AS secoes
           FROM marts.itajuba_local l WHERE l.ano = ? AND l.turno = ?
           GROUP BY l.ano, l.turno, l.nr_zona, l.nr_local_votacao
           ORDER BY l.nr_zona, l.nr_local_votacao""",
        p,
    )

    def cargos(grupo: dict[int, list]) -> list[dict]:
        return [{"codigo": cd, "votaveis": v} for cd, v in sorted(grupo.items())]

    return {
        "ano": ano,
        "turno": turno,
        "cargos": [
            {
                "codigo": cd,
                "nome": nomes_cargo.get(cd),
                "votaveis": v,
                "comparecimento": _comparecimento(comparecimento[cd])
                if cd in comparecimento
                else None,
            }
            for cd, v in sorted(por_cargo.items())
        ],
        "zonas": [{"zona": z, "cargos": cargos(g)} for (z,), g in sorted(zonas.items())],
        "locais": [
            {
                "zona": loc["nr_zona"],
                "local": loc["nr_local_votacao"],
                "nome": loc["nome"],
                "endereco": loc["endereco"],
                "bairro": loc["bairro"],
                "lat": loc["lat"],
                "lon": loc["lon"],
                "secoes": loc["secoes"] or [],
                "cargos": cargos(locais_votos.get((loc["nr_zona"], loc["nr_local_votacao"]), {})),
            }
            for loc in locais
        ],
    }


def _itajuba_secoes(con: duckdb.DuckDBPyConnection, ano: int, turno: int) -> dict:
    p = [ano, turno]
    votos = _linhas(
        con,
        """SELECT nr_zona, nr_secao, nr_local_votacao, cd_cargo, nr_votavel, votos
           FROM marts.itajuba_secao WHERE ano = ? AND turno = ?
           ORDER BY nr_zona, nr_secao, cd_cargo, votos DESC, nr_votavel""",
        p,
    )
    comparecimento = _linhas(
        con,
        """SELECT * FROM marts.itajuba_comparecimento WHERE ano = ? AND turno = ?
           ORDER BY nr_zona, nr_secao, cd_cargo""",
        p,
    )
    nomes = _linhas(
        con,
        """SELECT cd_cargo, nr_votavel,
                  any_value(coalesce(nm_urna_candidato, nm_votavel)) AS nome
           FROM marts.itajuba_secao
           WHERE ano = ? AND turno = ? AND nr_votavel NOT IN (95, 96)
           GROUP BY ALL ORDER BY cd_cargo, nr_votavel""",
        p,
    )
    secoes: dict[tuple, dict] = {}

    def secao(z: int, s: int, local: int | None) -> dict:
        return secoes.setdefault(
            (z, s), {"zona": z, "secao": s, "local": local, "comparecimento": {}, "votos": {}}
        )

    for c in comparecimento:
        secao(c["nr_zona"], c["nr_secao"], c["nr_local_votacao"])["comparecimento"][
            str(c["cd_cargo"])
        ] = {k: c[k] for k in ("aptos", "comparecimento", "abstencoes", "brancos", "nulos")}
    for v in votos:
        secao(v["nr_zona"], v["nr_secao"], v["nr_local_votacao"])["votos"].setdefault(
            str(v["cd_cargo"]), []
        ).append([v["nr_votavel"], v["votos"]])

    votaveis: dict[str, dict[str, str]] = {}
    for n in nomes:
        votaveis.setdefault(str(n["cd_cargo"]), {})[str(n["nr_votavel"])] = n["nome"]
    return {
        "ano": ano,
        "turno": turno,
        "votaveis": votaveis,
        "secoes": [secoes[k] for k in sorted(secoes)],
    }


def _historico(con: duckdb.DuckDBPyConnection) -> dict:
    partidos = _linhas(
        con,
        f"""SELECT ano, turno, cd_cargo AS cargo, nm_cargo AS nome_cargo, sg_partido AS partido,
                   votos, pct_validos
            FROM marts.historico_itajuba_partido WHERE cd_cargo IN {MAJORITARIOS}
            ORDER BY ano, turno, cd_cargo, votos DESC, sg_partido""",
    )
    comparecimento = _linhas(
        con,
        """SELECT ano, turno, cd_cargo AS cargo, nm_cargo AS nome_cargo, aptos, comparecimento,
                  abstencoes, brancos, nulos, pct_comparecimento, pct_abstencao
           FROM marts.historico_itajuba_comparecimento ORDER BY ano, turno, cd_cargo""",
    )
    for p in partidos:
        p["pct"] = _pct(p.pop("pct_validos"))
    for c in comparecimento:
        c["pct_comparecimento"] = _pct(c["pct_comparecimento"])
        c["pct_abstencao"] = _pct(c["pct_abstencao"])
    return {"partidos": partidos, "comparecimento": comparecimento}


def _manifesto(con: duckdb.DuckDBPyConnection, gerado_em: str, arquivos: dict[str, str]) -> dict:
    eleicoes: dict[int, list[int]] = {}
    for r in _linhas(con, "SELECT DISTINCT ano, turno FROM marts.resultado_uf ORDER BY ano, turno"):
        eleicoes.setdefault(r["ano"], []).append(r["turno"])
    municipio = _linhas(
        con,
        """SELECT s.cd_municipio AS codigo, s.nm_municipio AS nome, s.sg_uf AS uf,
                  any_value(i.cd_ibge) AS ibge
           FROM staging.votacao_secao s
           LEFT JOIN marts.municipio_ibge i USING (sg_uf, cd_municipio)
           GROUP BY s.cd_municipio, s.nm_municipio, s.sg_uf
           ORDER BY count(*) DESC LIMIT 1""",
    )
    origens = _linhas(
        con,
        """SELECT ano, turno, fonte, url, sha256, tamanho FROM staging.origens
           ORDER BY ano, turno, fonte""",
    )
    return {
        "schema_versao": SCHEMA_VERSAO,
        "gerado_em": gerado_em,
        "fonte": FONTE,
        "municipio": municipio[0] if municipio else None,
        "eleicoes": [{"ano": a, "turnos": t} for a, t in eleicoes.items()],
        "origens": origens,
        "arquivos": dict(sorted(arquivos.items())),
    }


# --- geração atômica -------------------------------------------------------------------


def _json(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def _json_compacto(obj: Any) -> bytes:
    """Arquivos grandes do mapa: sem indentação (o diff no PR não seria legível mesmo)."""
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _trocar(novo: Path, destino: Path) -> None:
    antigo = None
    if destino.exists():
        antigo = destino.with_name(f".{destino.name}.old-{uuid.uuid4().hex}")
        os.replace(destino, antigo)
    try:
        os.replace(novo, destino)
    except BaseException:
        if antigo is not None:
            os.replace(antigo, destino)
        raise
    if antigo is not None:
        shutil.rmtree(antigo)


def gerar_snapshots(
    con: duckdb.DuckDBPyConnection,
    destino: Path,
    *,
    gerado_em: str | None = None,
    validar: Callable[[Path], None] | None = None,
) -> dict:
    """Gera todos os snapshots e troca `destino` de uma vez. Devolve o manifesto.

    `validar` recebe o diretório temporário completo antes da troca (ex.: o
    verificador LGPD); se levantar exceção, nada é publicado.
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    gerado_em = gerado_em or datetime.now(UTC).isoformat(timespec="seconds")
    tmp = Path(tempfile.mkdtemp(prefix=f".{destino.name}.tmp-", dir=destino.parent))
    try:
        arquivos: dict[str, str] = {}

        def gravar(relativo: str, obj: Any, *, compacto: bool = False) -> None:
            gravar_bytes(relativo, _json_compacto(obj) if compacto else _json(obj))

        def gravar_bytes(relativo: str, corpo: bytes) -> None:
            caminho = tmp / relativo
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_bytes(corpo)
            arquivos[relativo] = hashlib.sha256(corpo).hexdigest()

        gravar_bytes("geo/municipios.topo.json", geometria.serializar(geometria.montar(con)))
        fotos: set[tuple[int, int]] = set()
        for f in _linhas(
            con,
            """SELECT ano, sq_candidato, any_value(jpeg ORDER BY turno) AS jpeg
               FROM staging.fotos_presidente GROUP BY ALL ORDER BY ALL""",
        ):
            gravar_bytes(_foto(f["ano"], f["sq_candidato"]), f["jpeg"])
            fotos.add((f["ano"], f["sq_candidato"]))
        ibge = {
            (r["sg_uf"], r["cd_municipio"]): r["cd_ibge"]
            for r in _linhas(
                con,
                "SELECT sg_uf, cd_municipio, cd_ibge FROM marts.municipio_ibge "
                "WHERE cd_ibge IS NOT NULL",
            )
        }
        sem_poligono = {
            r["cd_ibge"]: {"nome": r["nome"], "uf": r["sg_uf"]}
            for r in _linhas(
                con,
                """SELECT cd_ibge, sg_uf, coalesce(nm_ibge, nm_municipio) AS nome
                   FROM marts.municipio_ibge WHERE sem_poligono""",
            )
        }
        nomes_ibge = {
            r["cd_ibge"]: r["nm_municipio"]
            for r in _linhas(con, "SELECT cd_ibge, nm_municipio FROM staging.ibge_municipios")
        }

        particoes = _linhas(
            con, "SELECT DISTINCT ano, turno FROM marts.resultado_uf ORDER BY ano, turno"
        )
        for p in particoes:
            ano, turno = p["ano"], p["turno"]
            base = f"{ano}/{turno}"
            gravar(f"{base}/brasil.json", _brasil(con, ano, turno, fotos))
            cargos_turno = {
                r["cd_cargo"]
                for r in _linhas(
                    con,
                    "SELECT DISTINCT cd_cargo FROM marts.resultado_uf WHERE ano = ? AND turno = ?",
                    [ano, turno],
                )
            }
            for slug, (_, codigos, _) in CARGOS_MAPA.items():
                if not cargos_turno.intersection(codigos):
                    continue
                gravar(
                    f"{base}/mapa/{slug}.json",
                    _mapa(con, ano, turno, slug, ibge, sem_poligono),
                    compacto=True,
                )
                ufs_cargo = _linhas(
                    con,
                    f"""SELECT DISTINCT sg_uf FROM marts.comparecimento_municipio
                        WHERE ano = ? AND turno = ? AND cd_cargo IN {_cargos_sql(codigos)}
                          AND sg_uf <> 'ZZ' ORDER BY 1""",
                    [ano, turno],
                )
                for u in ufs_cargo:
                    gravar(
                        f"{base}/municipios/{u['sg_uf']}/{slug}.json",
                        _detalhe_uf(con, ano, turno, u["sg_uf"], slug, ibge, nomes_ibge),
                        compacto=True,
                    )
            ufs = _linhas(
                con,
                "SELECT DISTINCT sg_uf FROM marts.resultado_uf"
                " WHERE ano = ? AND turno = ? ORDER BY 1",
                [ano, turno],
            )
            for u in ufs:
                gravar(f"{base}/uf/{u['sg_uf']}.json", _uf(con, ano, turno, u["sg_uf"]))
            gravar(f"{base}/itajuba.json", _itajuba(con, ano, turno))
            gravar(f"{base}/itajuba_secoes.json", _itajuba_secoes(con, ano, turno))
        gravar("historico_itajuba.json", _historico(con))

        manifesto = _manifesto(con, gerado_em, arquivos)
        (tmp / "manifest.json").write_bytes(_json(manifesto))
        if validar is not None:
            validar(tmp)
        _trocar(tmp, destino)
        return manifesto
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --- trava de publicação ---------------------------------------------------------------


def eleicoes_removidas(anterior: dict | None, novo: dict) -> list[tuple[int, int]]:
    """(ano, turno) publicados em `anterior` que sumiriam em `novo`."""

    def pares(m: dict | None) -> set[tuple[int, int]]:
        return {(e["ano"], t) for e in (m or {}).get("eleicoes", []) for t in e["turnos"]}

    return sorted(pares(anterior) - pares(novo))


def main(argv: list[str] | None = None) -> int:
    """`python -m eleicoes.snapshots conferir <manifest anterior> <manifest novo>`

    Sai com 1 se a nova publicação apagaria alguma eleição já publicada.
    """
    import sys

    args = sys.argv[1:] if argv is None else argv
    if len(args) != 3 or args[0] != "conferir":
        print(main.__doc__)
        return 2
    anterior_p, novo_p = Path(args[1]), Path(args[2])
    anterior = json.loads(anterior_p.read_text(encoding="utf-8")) if anterior_p.exists() else None
    removidas = eleicoes_removidas(anterior, json.loads(novo_p.read_text(encoding="utf-8")))
    if removidas:
        lista = ", ".join(f"{a}/{t}" for a, t in removidas)
        print(
            f"ERRO: a nova publicação removeria {lista}. Sem MOTHERDUCK_TOKEN o banco do CI "
            "começa vazio: processe todas as eleições na mesma execução ou configure o token."
        )
        return 1
    print("Publicação conferida: nenhuma eleição publicada seria removida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
