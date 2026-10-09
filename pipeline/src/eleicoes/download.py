"""Download idempotente dos arquivos do TSE.

Cada arquivo é gravado primeiro em `<nome>.part` e só é renomeado depois de
completo; o manifest (`manifest.json` no diretório de destino) guarda URL,
tamanho, sha256 e data do download. Um arquivo já registrado e íntegro é
reutilizado sem nova requisição.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from eleicoes.fontes import Fonte

log = logging.getLogger(__name__)

CHUNK = 1024 * 1024


class FonteIndisponivel(RuntimeError):
    pass


class _ErroRetentavel(Exception):
    pass


@dataclass(frozen=True)
class ResultadoDownload:
    fonte: Fonte
    caminho: Path | None
    sha256: str | None
    baixado: bool


class Manifest:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._dados: dict[str, dict[str, Any]] = (
            json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        )

    def get(self, url: str) -> dict[str, Any] | None:
        return self._dados.get(url)

    def registrar(self, url: str, arquivo: Path, tamanho: int, sha256: str) -> None:
        self._dados[url] = {
            "url": url,
            "arquivo": arquivo.name,
            "tamanho": tamanho,
            "sha256": sha256,
            "baixado_em": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._dados, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)


def sha256_arquivo(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while bloco := f.read(CHUNK):
            h.update(bloco)
    return h.hexdigest()


def _integro(caminho: Path, entrada: dict[str, Any] | None) -> bool:
    return (
        entrada is not None
        and caminho.exists()
        and caminho.stat().st_size == entrada["tamanho"]
        and sha256_arquivo(caminho) == entrada["sha256"]
    )


def _baixar_para(client: httpx.Client, url: str, part: Path) -> tuple[int, str]:
    h = hashlib.sha256()
    tamanho = 0
    try:
        with client.stream("GET", url) as resp:
            if resp.status_code == 404:
                raise FonteIndisponivel(f"Arquivo não encontrado (404): {url}")
            if resp.status_code == 429 or resp.status_code >= 500:
                raise _ErroRetentavel(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            esperado = resp.headers.get("Content-Length")
            with part.open("wb") as f:
                for bloco in resp.iter_bytes(CHUNK):
                    f.write(bloco)
                    h.update(bloco)
                    tamanho += len(bloco)
    except httpx.TransportError as e:
        raise _ErroRetentavel(f"{type(e).__name__}: {e}") from e
    if esperado is not None and int(esperado) != tamanho:
        raise _ErroRetentavel(f"download incompleto ({tamanho} de {esperado} bytes)")
    return tamanho, h.hexdigest()


def baixar(
    fonte: Fonte,
    destino: Path,
    *,
    manifest: Manifest | None = None,
    client: httpx.Client | None = None,
    forcar: bool = False,
    tentativas: int = 4,
    backoff: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> ResultadoDownload:
    """Baixa `fonte` para `destino`, reutilizando o arquivo se já estiver íntegro.

    Arquivo obrigatório indisponível gera `FonteIndisponivel`; opcional gera um
    aviso e devolve `caminho=None`.
    """
    destino.mkdir(parents=True, exist_ok=True)
    manifest = manifest or Manifest(destino / "manifest.json")
    caminho = destino / fonte.arquivo
    entrada = manifest.get(fonte.url)

    if not forcar and _integro(caminho, entrada):
        log.info("Reutilizando %s (sha256 %s)", caminho.name, entrada["sha256"][:12])
        return ResultadoDownload(fonte, caminho, entrada["sha256"], baixado=False)

    part = caminho.with_name(caminho.name + ".part")
    proprio_client = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(60.0), follow_redirects=True)
    try:
        for tentativa in range(1, tentativas + 1):
            try:
                log.info("Baixando %s (tentativa %d/%d)", fonte.url, tentativa, tentativas)
                tamanho, sha = _baixar_para(client, fonte.url, part)
                os.replace(part, caminho)
                manifest.registrar(fonte.url, caminho, tamanho, sha)
                return ResultadoDownload(fonte, caminho, sha, baixado=True)
            except _ErroRetentavel as e:
                part.unlink(missing_ok=True)
                log.warning("Falha ao baixar %s: %s", fonte.url, e)
                if tentativa < tentativas:
                    sleep(backoff * 2 ** (tentativa - 1))
            except FonteIndisponivel:
                part.unlink(missing_ok=True)
                raise
        raise FonteIndisponivel(f"Falha após {tentativas} tentativas: {fonte.url}")
    except FonteIndisponivel as e:
        if fonte.obrigatoria:
            raise
        log.warning("Fonte opcional '%s' indisponível, seguindo sem ela: %s", fonte.nome, e)
        return ResultadoDownload(fonte, None, None, baixado=False)
    finally:
        if proprio_client:
            client.close()


def baixar_todas(
    fontes: Iterable[Fonte], destino: Path, **kwargs: Any
) -> dict[str, ResultadoDownload]:
    """Baixa todas as fontes com um único manifest e cliente HTTP."""
    destino.mkdir(parents=True, exist_ok=True)
    manifest = Manifest(destino / "manifest.json")
    with httpx.Client(timeout=httpx.Timeout(60.0), follow_redirects=True) as client:
        return {
            f.nome: baixar(f, destino, manifest=manifest, client=client, **kwargs) for f in fontes
        }
