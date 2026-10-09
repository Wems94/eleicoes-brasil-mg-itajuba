"""CLI `eleicoes`.

Exemplo: uv run eleicoes run --ano 2026 --turno 1
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Annotated

import typer

from eleicoes import pipeline
from eleicoes.config import DB_PATH, RAW_DIR, WEB_DATA_DIR
from eleicoes.download import FonteIndisponivel
from eleicoes.fontes import AnoNaoSuportado
from eleicoes.motherduck import GateNaoAprovado
from eleicoes.qualidade import QualidadeReprovada
from eleicoes.staging import MunicipioNaoEncontrado, SchemaDivergente, SemDados
from eleicoes.tse_csv import ColunaObrigatoriaAusente

app = typer.Typer(
    help="Pipeline das eleições gerais: TSE -> DuckDB -> MotherDuck e snapshots do site.",
    no_args_is_help=True,
    add_completion=False,
)

ERROS_ESPERADOS = (
    AnoNaoSuportado,
    FonteIndisponivel,
    SemDados,
    MunicipioNaoEncontrado,
    QualidadeReprovada,
    GateNaoAprovado,
    pipeline.VazamentoDetectado,
    pipeline.TurnoInvalido,
    ColunaObrigatoriaAusente,
    SchemaDivergente,
)


@app.callback()
def _raiz() -> None:
    """Mantém `run` como subcomando (há espaço para outros, como `snapshots`)."""


def _configurar_log() -> None:
    # Um handler novo a cada execução: o stderr pode ter sido trocado (ex.: testes).
    raiz = logging.getLogger("eleicoes")
    for h in list(raiz.handlers):
        if getattr(h, "_eleicoes_cli", False):
            raiz.removeHandler(h)
    h = logging.StreamHandler(sys.stderr)
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    h._eleicoes_cli = True  # type: ignore[attr-defined]
    raiz.addHandler(h)
    raiz.setLevel(logging.INFO)


@app.command()
def run(
    ano: Annotated[int, typer.Option(help="Ano da eleição (2018, 2022 ou 2026).")],
    turno: Annotated[int, typer.Option(help="Turno (1 ou 2).")],
    forcar: Annotated[bool, typer.Option(help="Baixa de novo mesmo se já existir.")] = False,
    db: Annotated[Path, typer.Option(help="Banco DuckDB local.")] = DB_PATH,
    raw: Annotated[Path, typer.Option(help="Diretório dos ZIPs do TSE.")] = RAW_DIR,
    snapshots: Annotated[Path, typer.Option(help="Diretório publicado do site.")] = WEB_DATA_DIR,
    sem_snapshots: Annotated[bool, typer.Option(help="Não gera os snapshots.")] = False,
    ufs: Annotated[
        str | None, typer.Option(help="UFs esperadas, separadas por vírgula.", hidden=True)
    ] = None,
    base_url: Annotated[str | None, typer.Option(help="URL base do TSE.", hidden=True)] = None,
) -> None:
    """Executa download, transformação, gate de qualidade, LGPD e publicação."""
    _configurar_log()
    try:
        r = pipeline.executar(
            ano,
            turno,
            db=db,
            raw=raw,
            snapshots=None if sem_snapshots else snapshots,
            forcar=forcar,
            ufs=[u.strip().upper() for u in ufs.split(",")] if ufs else None,
            base_url=base_url,
        )
    except ERROS_ESPERADOS as e:
        typer.echo(f"ERRO: {e}", err=True)
        raise typer.Exit(1) from e

    typer.echo(f"Gate de qualidade {ano}/{turno}: APROVADO")
    typer.echo(f"MotherDuck: {'enviado' if r.enviado_motherduck else 'carga remota pulada'}")
    if r.manifesto is not None:
        typer.echo(f"Snapshots: {len(r.manifesto['arquivos'])} arquivos em {snapshots}")
