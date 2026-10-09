"""Sincronização opcional com o MotherDuck (D4/D7).

Com token, o banco `eleicoes` no MotherDuck é a fonte da verdade do staging:
1. `baixar` antes de transformar (substitui o arquivo local pelo remoto);
2. transformar e validar localmente;
3. `enviar` só com o gate de qualidade aprovado (substitui o remoto de uma vez).
Sem token, nada é baixado nem enviado e o arquivo local é a única cópia.

Comandos conforme a documentação do MotherDuck (out/2026):
- COPY FROM DATABASE <remoto> TO <local anexado>
- CREATE OR REPLACE DATABASE <remoto> FROM '<arquivo local>'
A doc nomeia a variável `motherduck_token` (lida na conexão `md:`); aceitamos
também MOTHERDUCK_TOKEN no ambiente e repassamos com o nome documentado.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import duckdb

from eleicoes.qualidade import Relatorio

log = logging.getLogger(__name__)

TOKEN_VARS = ("MOTHERDUCK_TOKEN", "motherduck_token")
BANCO_PADRAO = "eleicoes"


class GateNaoAprovado(RuntimeError):
    pass


def obter_token(env: Mapping[str, str] | None = None) -> str | None:
    env = os.environ if env is None else env
    for nome in TOKEN_VARS:
        valor = (env.get(nome) or "").strip()
        if valor:
            return valor
    return None


class Remoto(Protocol):
    def existe(self) -> bool: ...
    def baixar_para(self, destino: Path) -> None: ...
    def substituir_por(self, origem: Path) -> None: ...


def _literal(caminho: Path) -> str:
    return "'" + str(caminho).replace("'", "''") + "'"


class MotherDuck:
    """Banco remoto no MotherDuck. Cada operação abre e fecha a própria conexão."""

    def __init__(self, token: str, banco: str = BANCO_PADRAO) -> None:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", banco):
            raise ValueError(f"nome de banco inválido: {banco!r}")
        self._token = token
        self.banco = banco

    def __repr__(self) -> str:  # nunca expõe o token
        return f"MotherDuck(banco={self.banco!r})"

    def _conectar(self) -> duckdb.DuckDBPyConnection:
        # Mecanismo documentado: variável `motherduck_token` + `md:`. Definida só
        # durante a conexão (o token fica fora da URL e de mensagens de erro).
        anterior = os.environ.get("motherduck_token")  # noqa: SIM112 (nome da doc)
        os.environ["motherduck_token"] = self._token  # noqa: SIM112
        try:
            return duckdb.connect("md:")
        finally:
            if anterior is None:
                os.environ.pop("motherduck_token", None)
            else:
                os.environ["motherduck_token"] = anterior  # noqa: SIM112

    def existe(self) -> bool:
        con = self._conectar()
        try:
            bancos = {
                r[0] for r in con.execute("SELECT database_name FROM duckdb_databases()").fetchall()
            }
        finally:
            con.close()
        return self.banco in bancos

    def baixar_para(self, destino: Path) -> None:
        con = self._conectar()
        try:
            con.execute(f"ATTACH {_literal(destino)} AS local_db")
            con.execute(f"COPY FROM DATABASE {self.banco} TO local_db")
            con.execute("DETACH local_db")
        finally:
            con.close()

    def substituir_por(self, origem: Path) -> None:
        con = self._conectar()
        try:
            con.execute(f"CREATE OR REPLACE DATABASE {self.banco} FROM {_literal(origem)}")
        finally:
            con.close()


def _remover_banco(caminho: Path) -> None:
    for p in (caminho, caminho.with_name(caminho.name + ".wal")):
        p.unlink(missing_ok=True)


@dataclass
class Sincronizador:
    token: str | None = field(repr=False)
    remoto: Remoto | None = None

    def __post_init__(self) -> None:
        if self.remoto is None and self.token:
            self.remoto = MotherDuck(self.token)

    @classmethod
    def do_ambiente(cls, env: Mapping[str, str] | None = None) -> Sincronizador:
        env = os.environ if env is None else env
        token = obter_token(env)
        banco = (env.get("MOTHERDUCK_DATABASE") or BANCO_PADRAO).strip()
        return cls(token=token, remoto=MotherDuck(token, banco) if token else None)

    @property
    def ativo(self) -> bool:
        return bool(self.token) and self.remoto is not None

    def baixar(self, local: Path) -> bool:
        """Substitui `local` pelo banco remoto. Feche conexões com `local` antes."""
        if not self.ativo:
            log.warning("MOTHERDUCK_TOKEN ausente: sem download, usando só o arquivo local")
            return False
        assert self.remoto is not None
        if not self.remoto.existe():
            log.info("Banco remoto inexistente: primeira carga, começando com arquivo vazio")
            _remover_banco(local)
            return False
        local.parent.mkdir(parents=True, exist_ok=True)
        tmp = local.with_name(local.name + ".tmp-download")
        _remover_banco(tmp)
        try:
            self.remoto.baixar_para(tmp)
            _remover_banco(local)
            os.replace(tmp, local)
        finally:
            _remover_banco(tmp)
        log.info("Banco remoto baixado para %s", local)
        return True

    def enviar(self, local: Path, relatorio: Relatorio | None) -> bool:
        """Substitui o banco remoto por `local`; exige o gate de qualidade aprovado."""
        if relatorio is None or not relatorio.ok:
            raise GateNaoAprovado("envio ao MotherDuck bloqueado: gate de qualidade não aprovado")
        if not self.ativo:
            log.warning("MOTHERDUCK_TOKEN ausente: carga remota pulada")
            return False
        assert self.remoto is not None
        self.remoto.substituir_por(local)
        log.info("Banco oficial no MotherDuck substituído a partir de %s", local)
        return True
