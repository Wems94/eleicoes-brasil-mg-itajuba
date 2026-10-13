"""Fotos de divulgação dos candidatos a Presidente (LGPD: só Presidente).

O pacote do TSE traz fotos de todos os candidatos com registro nacional; daqui
só saem as de quem disputa Presidente no (ano, turno) carregado, já reduzidas
a um tamanho fixo. Nenhuma outra foto é extraída do ZIP.
"""

from __future__ import annotations

import io
import logging
import re
import zipfile
from collections.abc import Iterable
from pathlib import Path

import duckdb
from PIL import Image, ImageOps

from eleicoes.fontes import Fonte

log = logging.getLogger(__name__)

SCHEMA = "staging"
LARGURA, ALTURA = 160, 200
QUALIDADE_JPEG = 82
DDL = f"""CREATE TABLE IF NOT EXISTS {SCHEMA}.fotos_presidente (
    ano INTEGER, turno INTEGER, sq_candidato BIGINT, jpeg BLOB)"""
# FBR280001607136_div.jpg -> 280001607136 (o sequencial vem logo antes de "_div")
_SQ = re.compile(r"(\d+)_div\.jpe?g$", re.IGNORECASE)


def sq_do_membro(nome: str) -> int | None:
    m = _SQ.search(Path(nome).name)
    return int(m.group(1)) if m else None


def reduzir(conteudo: bytes) -> bytes:
    """Recorta e reduz para LARGURA×ALTURA em JPEG, sem metadados (EXIF)."""
    with Image.open(io.BytesIO(conteudo)) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        img = ImageOps.fit(img, (LARGURA, ALTURA), Image.Resampling.LANCZOS, centering=(0.5, 0.3))
        saida = io.BytesIO()
        img.save(saida, "JPEG", quality=QUALIDADE_JPEG, optimize=True)
        return saida.getvalue()


def extrair(zip_path: Path, fonte: Fonte, presidentes: Iterable[int]) -> dict[int, bytes]:
    """sq_candidato -> JPEG reduzido, só para os `presidentes` presentes no ZIP."""
    alvo = set(presidentes)
    out: dict[int, bytes] = {}
    with zipfile.ZipFile(zip_path) as z:
        for nome in fonte.selecionar_membros(z.namelist()):
            sq = sq_do_membro(nome)
            if sq is None or sq not in alvo or sq in out:
                continue
            try:
                out[sq] = reduzir(z.read(nome))
            except OSError as e:  # imagem corrompida: segue sem ela
                log.warning("Foto %s ignorada: %s", nome, e)
    faltando = alvo - out.keys()
    if faltando:
        log.warning("Sem foto no pacote do TSE para %d candidato(s) a Presidente", len(faltando))
    return out


def carregar(
    con: duckdb.DuckDBPyConnection, ano: int, turno: int, zip_path: Path, fonte: Fonte
) -> int:
    """Grava as fotos dos presidenciáveis do (ano, turno); a partição já foi apagada."""
    presidentes = [
        sq
        for (sq,) in con.execute(
            f"""SELECT DISTINCT sq_candidato FROM {SCHEMA}.votacao_munzona
                WHERE ano = ? AND turno = ? AND cd_cargo = 1""",
            [ano, turno],
        ).fetchall()
    ]
    fotos = extrair(zip_path, fonte, presidentes)
    con.executemany(
        f"INSERT INTO {SCHEMA}.fotos_presidente VALUES (?, ?, ?, ?)",
        [(ano, turno, sq, jpeg) for sq, jpeg in sorted(fotos.items())],
    )
    return len(fotos)
