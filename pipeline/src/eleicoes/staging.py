"""Carga do staging (schema `staging`) por partição (ano, turno), D4 e D5.

Recarregar um (ano, turno) é, numa única transação, `DELETE` da partição em
todas as tabelas seguido do `INSERT` da nova carga: uma falha no meio deixa a
partição anterior intacta, e as outras partições nunca são tocadas.
"""

from __future__ import annotations

import logging
import tempfile
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import duckdb
import yaml

from eleicoes import esquema
from eleicoes.config import CONFIG_DIR
from eleicoes.download import ResultadoDownload, sha256_arquivo
from eleicoes.tse_csv import Tabela, select_sql

log = logging.getLogger(__name__)

SCHEMA = "staging"
PRESIDENTE = 1
ELEICAO_ORDINARIA = 2
# Arquivos do TSE usados em cada partição (para o manifesto dos snapshots, 5.2).
ORIGENS_DDL = f"""CREATE TABLE IF NOT EXISTS {SCHEMA}.origens (
    ano INTEGER, turno INTEGER, fonte VARCHAR, url VARCHAR, sha256 VARCHAR, tamanho BIGINT)"""


class SchemaDivergente(RuntimeError):
    pass


class MunicipioNaoEncontrado(RuntimeError):
    pass


class SemDados(RuntimeError):
    pass


@dataclass(frozen=True)
class Recorte:
    uf: str
    municipio: str

    @classmethod
    def carregar(cls, path: Path = CONFIG_DIR / "eleicoes.yaml") -> Recorte:
        r = yaml.safe_load(path.read_text(encoding="utf-8"))["recorte_municipal"]
        return cls(uf=r["uf"], municipio=r["municipio"])


@dataclass
class ResumoCarga:
    ano: int
    turno: int
    cd_municipio: int
    fallback_presidente: bool
    linhas: dict[str, int] = field(default_factory=dict)
    fontes_ausentes: list[str] = field(default_factory=list)


def criar_tabelas(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    con.execute(ORIGENS_DDL)
    for t in esquema.TABELAS:
        con.execute(t.ddl(SCHEMA))
        existentes = [
            (nome, tipo)
            for nome, tipo in con.execute(
                """SELECT column_name, data_type FROM information_schema.columns
                   WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position""",
                [SCHEMA, t.nome],
            ).fetchall()
        ]
        esperadas = [(c.nome, c.tipo) for c in t.colunas]
        if existentes != esperadas:
            raise SchemaDivergente(
                f"{SCHEMA}.{t.nome} existe com colunas diferentes do esquema atual; "
                f"recrie a tabela (esperado {esperadas}, encontrado {existentes})"
            )


def extrair(download: ResultadoDownload, destino: Path) -> list[Path]:
    """Extrai do ZIP só os membros previstos no catálogo (nunca o _BRASIL)."""
    assert download.caminho is not None
    destino.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(download.caminho) as z:
        membros = download.fonte.selecionar_membros(z.namelist())
        if not membros:
            raise FileNotFoundError(
                f"{download.caminho.name}: nenhum membro corresponde a {download.fonte.membros}"
            )
        return [Path(z.extract(m, destino)) for m in membros]


def resolver_municipio(
    con: duckdb.DuckDBPyConnection, ano: int, turno: int, recorte: Recorte
) -> int:
    """Código TSE do município do recorte, pelo nome e UF nos próprios dados."""
    achados = con.execute(
        f"""SELECT DISTINCT cd_municipio, nm_municipio FROM {SCHEMA}.detalhe_munzona
            WHERE ano = ? AND turno = ? AND sg_uf = ?
              AND upper(strip_accents(nm_municipio)) = upper(strip_accents(?))
            ORDER BY cd_municipio""",
        [ano, turno, recorte.uf, recorte.municipio],
    ).fetchall()
    if len({cd for cd, _ in achados}) != 1:
        detalhe = ", ".join(f"{cd} ({nm})" for cd, nm in achados) or "nenhum"
        raise MunicipioNaoEncontrado(
            f"{recorte.municipio}/{recorte.uf} em {ano} turno {turno}: esperado 1 código TSE, "
            f"encontrado: {detalhe}"
        )
    return achados[0][0]


@cache
def _cargos(path: Path = CONFIG_DIR / "eleicoes.yaml") -> tuple[int, ...]:
    return tuple(yaml.safe_load(path.read_text(encoding="utf-8"))["cargos"])


def _inserir(
    con: duckdb.DuckDBPyConnection,
    tabela: Tabela,
    arquivos: Sequence[Path],
    ano: int,
    turno: int,
    filtro: str = "TRUE",
    params: Sequence[object] = (),
) -> int:
    # Só a eleição geral: descarta eleições extraordinárias (ex.: suplementar de Senado)
    # e cargos fora do domínio (ex.: Conselheiro Distrital de Fernando de Noronha).
    colunas = {c.nome for c in tabela.colunas}
    if "cd_tipo_eleicao" in colunas:
        filtro = (
            f"({filtro}) AND coalesce(cd_tipo_eleicao, {ELEICAO_ORDINARIA}) = {ELEICAO_ORDINARIA}"
        )
    if "cd_cargo" in colunas:
        filtro = f"({filtro}) AND cd_cargo IN ({', '.join(map(str, _cargos()))})"
    (antes,) = con.execute(
        f"SELECT count(*) FROM {SCHEMA}.{tabela.nome} WHERE ano = ? AND turno = ?", [ano, turno]
    ).fetchone()
    con.execute(
        f"""INSERT INTO {SCHEMA}.{tabela.nome} BY NAME
            SELECT * FROM ({select_sql(tabela, arquivos)})
            WHERE ano = ? AND turno = ? AND ({filtro})""",
        [ano, turno, *params],
    )
    (depois,) = con.execute(
        f"SELECT count(*) FROM {SCHEMA}.{tabela.nome} WHERE ano = ? AND turno = ?", [ano, turno]
    ).fetchone()
    return depois - antes


def _tem_presidente(con: duckdb.DuckDBPyConnection, tabela: Tabela, ano: int, turno: int) -> bool:
    return bool(
        con.execute(
            f"""SELECT count(*) FROM {SCHEMA}.{tabela.nome}
                WHERE ano = ? AND turno = ? AND cd_cargo = {PRESIDENTE}""",
            [ano, turno],
        ).fetchone()[0]
    )


def carregar_particao(
    con: duckdb.DuckDBPyConnection,
    ano: int,
    turno: int,
    downloads: Mapping[str, ResultadoDownload],
    trabalho: Path,
    recorte: Recorte | None = None,
) -> ResumoCarga:
    """Substitui a partição (ano, turno) do staging a partir dos ZIPs baixados."""
    recorte = recorte or Recorte.carregar()
    criar_tabelas(con)
    trabalho.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=trabalho) as tmp:
        arquivos: dict[str, list[Path]] = {}
        for nome, d in downloads.items():
            if d.caminho is None:
                arquivos[nome] = []
                continue
            try:
                arquivos[nome] = extrair(d, Path(tmp) / nome)
            except FileNotFoundError as e:
                if d.fonte.obrigatoria:
                    raise
                log.warning("Fonte opcional '%s' ignorada (layout inesperado): %s", nome, e)
                arquivos[nome] = []
        det_secao = arquivos.get("detalhe_votacao_secao", [])
        det_secao_br = [a for a in det_secao if a.name.endswith("_BR.csv")]
        det_secao_uf = [a for a in det_secao if a not in det_secao_br]

        con.execute("BEGIN TRANSACTION")
        try:
            for nome in [t.nome for t in esquema.TABELAS] + ["origens"]:
                con.execute(
                    f"DELETE FROM {SCHEMA}.{nome} WHERE ano = ? AND turno = ?", [ano, turno]
                )
            linhas = {t.nome: 0 for t in esquema.TABELAS}

            def carregar(tabela: Tabela, arqs: Sequence[Path], filtro="TRUE", params=()):
                linhas[tabela.nome] += _inserir(con, tabela, arqs, ano, turno, filtro, params)

            carregar(esquema.VOTACAO_MUNZONA, arquivos.get("votacao_candidato_munzona", []))
            carregar(esquema.DETALHE_MUNZONA, arquivos.get("detalhe_votacao_munzona", []))
            if linhas[esquema.VOTACAO_MUNZONA.nome] == 0:
                raise SemDados(
                    f"Nenhuma linha de votação para {ano} turno {turno} nos arquivos do TSE "
                    "(o turno já aconteceu e foi publicado?)"
                )

            cd = resolver_municipio(con, ano, turno, recorte)
            do_municipio = ("sg_uf = ? AND cd_municipio = ?", (recorte.uf, cd))
            so_presidente = (f"{do_municipio[0]} AND cd_cargo = {PRESIDENTE}", do_municipio[1])

            carregar(esquema.VOTACAO_SECAO, arquivos.get("votacao_secao_mg", []), *do_municipio)
            fallback = not _tem_presidente(con, esquema.VOTACAO_SECAO, ano, turno)
            if fallback:
                log.info("Presidente ausente no arquivo de seção de MG; usando o arquivo _BR")
                carregar(
                    esquema.VOTACAO_SECAO, arquivos.get("votacao_secao_br", []), *so_presidente
                )

            carregar(esquema.DETALHE_SECAO, det_secao_uf, *do_municipio)
            if not _tem_presidente(con, esquema.DETALHE_SECAO, ano, turno) and det_secao_br:
                carregar(esquema.DETALHE_SECAO, det_secao_br, *so_presidente)

            ausentes = []
            for fonte, tabela, filtro in (
                ("consulta_cand", esquema.CANDIDATOS, ("TRUE", ())),
                ("locais_votacao", esquema.LOCAIS_VOTACAO, do_municipio),
            ):
                if arquivos.get(fonte):
                    carregar(tabela, arquivos[fonte], *filtro)
                else:
                    log.warning("Fonte opcional '%s' ausente em %d turno %d", fonte, ano, turno)
                    ausentes.append(fonte)

            for nome, d in downloads.items():
                if arquivos.get(nome) and d.caminho is not None:
                    con.execute(
                        f"INSERT INTO {SCHEMA}.origens VALUES (?, ?, ?, ?, ?, ?)",
                        [
                            ano,
                            turno,
                            nome,
                            d.fonte.url,
                            d.sha256 or sha256_arquivo(d.caminho),
                            d.caminho.stat().st_size,
                        ],
                    )

            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

    resumo = ResumoCarga(ano, turno, cd, fallback, linhas, ausentes)
    log.info("Staging %d/%d carregado: %s", ano, turno, linhas)
    return resumo
