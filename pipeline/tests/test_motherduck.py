import logging
import os
import shutil
from pathlib import Path

import duckdb
import pytest

from eleicoes.motherduck import (
    GateNaoAprovado,
    MotherDuck,
    Sincronizador,
    obter_token,
)
from eleicoes.qualidade import Regra, Relatorio, Resultado

TOKEN = "tok-secreto-123"


class RemotoFalso:
    """Banco remoto simulado por um arquivo DuckDB (mesma interface do MotherDuck)."""

    def __init__(self, caminho: Path) -> None:
        self.caminho = caminho
        self.envios = 0

    def existe(self) -> bool:
        return self.caminho.exists()

    def baixar_para(self, destino: Path) -> None:
        shutil.copy(self.caminho, destino)

    def substituir_por(self, origem: Path) -> None:
        self.envios += 1
        shutil.copy(origem, self.caminho)


def _banco(caminho: Path, valor: int) -> Path:
    con = duckdb.connect(str(caminho))
    con.execute("CREATE SCHEMA staging")
    con.execute("CREATE TABLE staging.t AS SELECT ? AS v", [valor])
    con.close()
    return caminho


def _valor(caminho: Path) -> int:
    con = duckdb.connect(str(caminho), read_only=True)
    try:
        return con.execute("SELECT v FROM staging.t").fetchone()[0]
    finally:
        con.close()


def _relatorio(ok: bool) -> Relatorio:
    regra = Regra("r", "regra de teste", "SELECT 1")
    return Relatorio(2026, 1, [Resultado(regra, 0 if ok else 1)])


@pytest.fixture
def remoto(tmp_path) -> RemotoFalso:
    return RemotoFalso(tmp_path / "remoto" / "eleicoes.duckdb")


# --- token -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("env", "esperado"),
    [
        ({"MOTHERDUCK_TOKEN": TOKEN}, TOKEN),
        ({"motherduck_token": TOKEN}, TOKEN),  # nome usado na documentação do MotherDuck
        ({"MOTHERDUCK_TOKEN": "  "}, None),
        ({"MOTHERDUCK_TOKEN": ""}, None),
        ({}, None),
    ],
)
def test_token_lido_das_duas_grafias(env, esperado):
    assert obter_token(env) == esperado


# --- sem token: tudo é pulado ---------------------------------------------------------


def test_sem_token_nao_baixa_nem_envia(tmp_path, remoto, caplog):
    remoto.caminho.parent.mkdir(parents=True)
    _banco(remoto.caminho, 1)
    local = _banco(tmp_path / "local.duckdb", 2)
    sinc = Sincronizador(token=None, remoto=remoto)

    with caplog.at_level(logging.WARNING):
        assert sinc.baixar(local) is False
        assert sinc.enviar(local, _relatorio(ok=True)) is False

    assert _valor(local) == 2  # local intacto
    assert _valor(remoto.caminho) == 1  # remoto intacto
    assert remoto.envios == 0
    assert "MOTHERDUCK_TOKEN" in caplog.text


def test_sem_token_nunca_cria_conexao_com_o_motherduck(tmp_path, monkeypatch):
    """Sem token o MotherDuck abre o navegador para autenticar: travaria o CI."""

    def proibido(*a, **k):
        raise AssertionError("não pode conectar sem token")

    monkeypatch.setattr(duckdb, "connect", proibido)
    sinc = Sincronizador.do_ambiente({})
    assert sinc.baixar(tmp_path / "x.duckdb") is False
    assert sinc.enviar(tmp_path / "x.duckdb", _relatorio(ok=True)) is False


# --- com token -----------------------------------------------------------------------


def test_baixar_substitui_o_arquivo_local_pelo_remoto(tmp_path, remoto):
    remoto.caminho.parent.mkdir(parents=True)
    _banco(remoto.caminho, 1)
    local = _banco(tmp_path / "local.duckdb", 99)  # cópia local desatualizada

    assert Sincronizador(token=TOKEN, remoto=remoto).baixar(local) is True
    assert _valor(local) == 1
    assert not list(tmp_path.glob("*.tmp*"))


def test_primeira_carga_comeca_com_arquivo_vazio(tmp_path, remoto, caplog):
    """Com token e sem banco remoto, a execução parte do zero: uma cópia local
    antiga não pode virar a 'verdade' no próximo envio (D4)."""
    local = _banco(tmp_path / "local.duckdb", 99)

    with caplog.at_level(logging.INFO):
        assert Sincronizador(token=TOKEN, remoto=remoto).baixar(local) is False

    assert not local.exists()
    assert "primeira carga" in caplog.text


def test_falha_no_download_preserva_o_arquivo_local(tmp_path, remoto):
    remoto.caminho.parent.mkdir(parents=True)
    _banco(remoto.caminho, 1)
    local = _banco(tmp_path / "local.duckdb", 2)

    def quebra(destino):
        destino.write_bytes(b"parcial")
        raise ConnectionError("rede caiu")

    remoto.baixar_para = quebra
    with pytest.raises(ConnectionError):
        Sincronizador(token=TOKEN, remoto=remoto).baixar(local)

    assert _valor(local) == 2
    assert not list(tmp_path.glob("*.tmp*"))


def test_enviar_apos_gate_aprovado(tmp_path, remoto):
    remoto.caminho.parent.mkdir(parents=True)
    local = _banco(tmp_path / "local.duckdb", 7)

    assert Sincronizador(token=TOKEN, remoto=remoto).enviar(local, _relatorio(ok=True)) is True
    assert _valor(remoto.caminho) == 7
    assert remoto.envios == 1


def test_envio_nao_ocorre_se_o_gate_falhar(tmp_path, remoto):
    remoto.caminho.parent.mkdir(parents=True)
    _banco(remoto.caminho, 1)
    local = _banco(tmp_path / "local.duckdb", 666)

    with pytest.raises(GateNaoAprovado):
        Sincronizador(token=TOKEN, remoto=remoto).enviar(local, _relatorio(ok=False))

    assert remoto.envios == 0
    assert _valor(remoto.caminho) == 1


def test_envio_exige_relatorio_do_gate(tmp_path, remoto):
    with pytest.raises(GateNaoAprovado):
        Sincronizador(token=TOKEN, remoto=remoto).enviar(tmp_path / "x.duckdb", None)


# --- SQL real do MotherDuck (sem rede: conexão gravadora) -------------------------------


class ConexaoGravadora:
    def __init__(self, bancos: list[str]) -> None:
        self.bancos = bancos
        self.sql: list[tuple[str, list]] = []
        self.fechada = False

    def execute(self, sql, params=None):
        self.sql.append((" ".join(sql.split()), params or []))
        return self

    def fetchall(self):
        return [(b,) for b in self.bancos]

    def close(self):
        self.fechada = True


def test_motherduck_usa_os_comandos_documentados(tmp_path, monkeypatch):
    monkeypatch.delenv("motherduck_token", raising=False)
    con = ConexaoGravadora(["eleicoes", "my_db"])
    conexoes = []

    def conectar(dsn, **kwargs):
        conexoes.append((dsn, os.environ.get("motherduck_token")))  # noqa: SIM112
        return con

    monkeypatch.setattr(duckdb, "connect", conectar)
    md = MotherDuck(TOKEN, banco="eleicoes")

    assert md.existe()
    md.baixar_para(tmp_path / "novo.duckdb")
    md.substituir_por(tmp_path / "local.duckdb")

    # token pela variável documentada, só durante a conexão, e fora da URL
    assert conexoes and all(c == ("md:", TOKEN) for c in conexoes)
    assert os.environ.get("motherduck_token") is None  # noqa: SIM112
    comandos = [s for s, _ in con.sql]
    assert f"ATTACH '{tmp_path / 'novo.duckdb'}' AS local_db" in comandos
    assert "COPY FROM DATABASE eleicoes TO local_db" in comandos
    assert f"CREATE OR REPLACE DATABASE eleicoes FROM '{tmp_path / 'local.duckdb'}'" in comandos
    assert con.fechada


def test_token_nao_aparece_nos_logs(tmp_path, remoto, caplog):
    remoto.caminho.parent.mkdir(parents=True)
    _banco(remoto.caminho, 1)
    with caplog.at_level(logging.DEBUG):
        sinc = Sincronizador(token=TOKEN, remoto=remoto)
        sinc.baixar(tmp_path / "local.duckdb")
        sinc.enviar(tmp_path / "local.duckdb", _relatorio(ok=True))
    assert TOKEN not in caplog.text
    assert TOKEN not in repr(sinc)
