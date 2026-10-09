"""Orquestração de uma execução (ano, turno), na ordem do design:

download -> baixar MotherDuck -> staging -> marts -> gate de qualidade -> LGPD
-> enviar MotherDuck -> snapshots (validados pelo LGPD antes da troca).

Qualquer falha interrompe a execução antes de publicar: o MotherDuck e os
snapshots só mudam depois do gate e do verificador LGPD.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import duckdb

from eleicoes.download import baixar_todas
from eleicoes.fontes import Catalogo
from eleicoes.lgpd import Vazamento, verificar_banco, verificar_snapshots
from eleicoes.marts import construir_marts
from eleicoes.motherduck import Sincronizador
from eleicoes.qualidade import Relatorio, gate
from eleicoes.snapshots import gerar_snapshots
from eleicoes.staging import ResumoCarga, carregar_particao

log = logging.getLogger(__name__)

TURNOS = (1, 2)


class TurnoInvalido(ValueError):
    pass


class VazamentoDetectado(RuntimeError):
    def __init__(self, onde: str, vazamentos: list[Vazamento]) -> None:
        detalhe = "\n".join(f"  [ERRO] {v}" for v in vazamentos)
        super().__init__(f"LGPD: {len(vazamentos)} vazamento(s) em {onde}\n{detalhe}")
        self.vazamentos = vazamentos


@dataclass(frozen=True)
class ResultadoExecucao:
    carga: ResumoCarga
    relatorio: Relatorio
    enviado_motherduck: bool
    manifesto: dict | None


def _verificar_snapshots(diretorio: Path) -> None:
    vazamentos = verificar_snapshots(diretorio)
    if vazamentos:
        raise VazamentoDetectado("snapshots", vazamentos)


def executar(
    ano: int,
    turno: int,
    *,
    db: Path,
    raw: Path,
    snapshots: Path | None,
    forcar: bool = False,
    ufs: Sequence[str] | None = None,
    base_url: str | None = None,
    sincronizador: Sincronizador | None = None,
) -> ResultadoExecucao:
    catalogo = Catalogo.carregar(base_url=base_url)
    catalogo.validar_ano(ano)
    if turno not in TURNOS:
        raise TurnoInvalido(f"Turno {turno} inválido; use 1 ou 2.")

    downloads = baixar_todas(catalogo.resolver(ano), raw, forcar=forcar)

    sinc = sincronizador or Sincronizador.do_ambiente()
    db.parent.mkdir(parents=True, exist_ok=True)
    sinc.baixar(db)  # com token, o banco remoto substitui a cópia local (D4)

    con = duckdb.connect(str(db))
    try:
        carga = carregar_particao(con, ano, turno, downloads, db.parent / "trabalho")
        construir_marts(con)
        relatorio = gate(con, ano, turno, ufs=ufs)
        log.info("\n%s", relatorio.texto())
        vazamentos = verificar_banco(con)
        if vazamentos:
            raise VazamentoDetectado("banco", vazamentos)
        con.execute("CHECKPOINT")
    finally:
        con.close()

    enviado = sinc.enviar(db, relatorio)

    manifesto = None
    if snapshots is not None:
        con = duckdb.connect(str(db), read_only=True)
        try:
            manifesto = gerar_snapshots(con, snapshots, validar=_verificar_snapshots)
        finally:
            con.close()
        log.info("Snapshots publicados em %s (%d arquivos)", snapshots, len(manifesto["arquivos"]))

    return ResultadoExecucao(carga, relatorio, enviado, manifesto)
