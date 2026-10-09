"""Testes ponta a ponta da CLI `eleicoes run` com os fixtures servidos por HTTP local."""

import json
import re
from pathlib import Path

import duckdb
import pytest
from typer.testing import CliRunner

from eleicoes import snapshots
from eleicoes.cli import app
from eleicoes.motherduck import Sincronizador
from tests.conftest import TSE, montar_zips
from tests.servidor_http import servidor_http
from tests.test_motherduck import RemotoFalso

UFS = "MG,SP"  # os fixtures só têm MG e SP
# No GitHub Actions o Rich colore a saída e os códigos ANSI quebram o texto ("--ano").
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _saida(r) -> str:
    return ANSI.sub("", r.output)


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    """Servidor com os ZIPs de 2018 e 2022 e caminhos isolados em tmp_path."""
    monkeypatch.delenv("MOTHERDUCK_TOKEN", raising=False)
    monkeypatch.delenv("motherduck_token", raising=False)  # noqa: SIM112
    with servidor_http() as srv:

        def publicar(ano: int, **kwargs) -> None:
            for d in montar_zips(ano, tmp_path / "zips" / str(ano), **kwargs).values():
                if d.caminho is not None:
                    srv.arquivos[d.fonte.url.split("odsele/", 1)[1]] = d.caminho.read_bytes()

        publicar(2018)
        publicar(2022)
        srv.publicar = publicar
        srv.tmp = tmp_path
        yield srv


def _args(srv, ano=2022, turno=1, *extra) -> list[str]:
    t = srv.tmp
    return [
        "run",
        "--ano", str(ano),
        "--turno", str(turno),
        "--db", str(t / "data" / "eleicoes.duckdb"),
        "--raw", str(t / "data" / "raw"),
        "--snapshots", str(t / "web" / "data"),
        "--ufs", UFS,
        "--base-url", srv.base_url,
        *extra,
    ]  # fmt: skip


def _rodar(srv, *args, **kwargs):
    return CliRunner().invoke(app, _args(srv, *args, **kwargs), catch_exceptions=False)


def _manifesto(srv) -> dict:
    return json.loads((srv.tmp / "web" / "data" / "manifest.json").read_text(encoding="utf-8"))


def _particoes(srv) -> set[tuple[int, int]]:
    con = duckdb.connect(str(srv.tmp / "data" / "eleicoes.duckdb"), read_only=True)
    try:
        return set(
            con.execute("SELECT DISTINCT ano, turno FROM staging.votacao_munzona").fetchall()
        )
    finally:
        con.close()


def _arvore(d: Path) -> dict[str, bytes]:
    return {
        p.relative_to(d).as_posix(): p.read_bytes() for p in sorted(d.rglob("*")) if p.is_file()
    }


def test_help():
    r = CliRunner().invoke(app, ["run", "--help"])
    assert r.exit_code == 0
    assert "--ano" in _saida(r) and "--turno" in _saida(r)


def test_ponta_a_ponta_sem_token(ambiente):
    r = _rodar(ambiente, 2022, 1)

    assert r.exit_code == 0, _saida(r)
    assert _particoes(ambiente) == {(2022, 1)}
    m = _manifesto(ambiente)
    assert m["eleicoes"] == [{"ano": 2022, "turnos": [1]}]
    assert (ambiente.tmp / "web" / "data" / "2022" / "1" / "itajuba.json").exists()
    assert "carga remota pulada" in _saida(r)
    assert "APROVADO" in _saida(r)


def test_turnos_e_anos_se_acumulam_no_banco_e_no_manifesto(ambiente):
    assert _rodar(ambiente, 2022, 1).exit_code == 0
    assert _rodar(ambiente, 2022, 2).exit_code == 0
    assert _rodar(ambiente, 2018, 1).exit_code == 0

    assert _particoes(ambiente) == {(2022, 1), (2022, 2), (2018, 1)}
    assert _manifesto(ambiente)["eleicoes"] == [
        {"ano": 2018, "turnos": [1]},
        {"ano": 2022, "turnos": [1, 2]},
    ]


def test_reexecucao_nao_baixa_de_novo(ambiente):
    _rodar(ambiente, 2022, 1)
    antes = sum(ambiente.requisicoes.values())
    assert _rodar(ambiente, 2022, 1).exit_code == 0
    assert sum(ambiente.requisicoes.values()) == antes


def test_ano_nao_suportado(ambiente):
    r = CliRunner().invoke(app, _args(ambiente, 2020, 1))
    assert r.exit_code != 0
    assert "2018, 2022, 2026" in _saida(r)


def test_fonte_obrigatoria_ausente_nao_publica_nada(ambiente):
    del ambiente.arquivos["votacao_candidato_munzona/votacao_candidato_munzona_2022.zip"]
    r = _rodar(ambiente, 2022, 1)
    assert r.exit_code == 1
    assert "votacao_candidato_munzona_2022.zip" in _saida(r)
    assert not (ambiente.tmp / "web" / "data").exists()


def _corromper_secao_de_itajuba(ambiente) -> None:
    det = (TSE / "2022" / "detalhe_votacao_secao_2022_MG.csv").read_bytes().splitlines()
    linhas = [det[0]]
    for lin in det[1:]:
        c = lin.split(b";")
        if c[13] == b"46477" and c[16] == b"18":  # Itajubá, seção 18: comparecimento + 1
            c[20] = str(int(c[20]) + 1).encode()
        linhas.append(b";".join(c))
    ambiente.publicar(2022, substituir={"detalhe_votacao_secao_2022_MG.csv": b"\n".join(linhas)})


def test_gate_reprovado_nao_publica_nem_envia(ambiente, monkeypatch):
    remoto = RemotoFalso(ambiente.tmp / "md" / "eleicoes.duckdb")
    monkeypatch.setattr(
        Sincronizador, "do_ambiente", classmethod(lambda cls, env=None: cls("tok", remoto))
    )
    assert _rodar(ambiente, 2018, 1).exit_code == 0  # publicação anterior válida
    antes = _arvore(ambiente.tmp / "web" / "data")
    envios_antes = remoto.envios

    _corromper_secao_de_itajuba(ambiente)
    r = _rodar(ambiente, 2022, 1, "--forcar")

    assert r.exit_code == 1
    assert "soma_secao_itajuba" in _saida(r)
    assert remoto.envios == envios_antes  # MotherDuck intacto
    assert _arvore(ambiente.tmp / "web" / "data") == antes  # snapshots anteriores mantidos


def test_com_token_baixa_antes_e_envia_depois(ambiente, monkeypatch):
    """D4: o banco remoto (com 2018) é baixado, 2022/1 é somado e tudo volta ao remoto."""
    remoto = RemotoFalso(ambiente.tmp / "md" / "eleicoes.duckdb")
    monkeypatch.setattr(
        Sincronizador, "do_ambiente", classmethod(lambda cls, env=None: cls("tok", remoto))
    )
    assert _rodar(ambiente, 2018, 1).exit_code == 0  # 1ª carga: remoto vazio -> criado
    assert remoto.envios == 1
    (ambiente.tmp / "data" / "eleicoes.duckdb").unlink()  # outra máquina, sem cópia local

    r = _rodar(ambiente, 2022, 1)

    assert r.exit_code == 0, _saida(r)
    assert remoto.envios == 2
    assert _particoes(ambiente) == {(2018, 1), (2022, 1)}
    con = duckdb.connect(str(remoto.caminho), read_only=True)
    try:
        assert set(
            con.execute("SELECT DISTINCT ano, turno FROM staging.votacao_munzona").fetchall()
        ) == {(2018, 1), (2022, 1)}
    finally:
        con.close()


def test_vazamento_nos_snapshots_bloqueia_a_publicacao(ambiente, monkeypatch):
    assert _rodar(ambiente, 2022, 1).exit_code == 0
    antes = _arvore(ambiente.tmp / "web" / "data")
    original = snapshots._brasil

    def com_vazamento(*a, **k):
        d = original(*a, **k)
        d["contato"] = "candidato@exemplo.com.br"
        return d

    monkeypatch.setattr(snapshots, "_brasil", com_vazamento)
    r = _rodar(ambiente, 2022, 1)

    assert r.exit_code == 1
    assert "LGPD" in _saida(r)
    assert "candidato@exemplo.com.br" not in _saida(r)  # mascarado
    assert _arvore(ambiente.tmp / "web" / "data") == antes


def test_turno_sem_dados(ambiente):
    def sem_turno_2(nome: str) -> bytes:
        linhas = (TSE / "2022" / nome).read_bytes().splitlines()
        return b"\n".join(lin for lin in linhas if lin.split(b";")[5] != b"2") + b"\n"

    ambiente.publicar(
        2022,
        substituir={
            f"{d}_2022_{m}.csv": sem_turno_2(f"{d}_2022_{m}.csv")
            for d in ("votacao_candidato_munzona", "detalhe_votacao_munzona")
            for m in ("MG", "SP", "BR")
        },
    )
    r = _rodar(ambiente, 2022, 2)
    assert r.exit_code == 1
    assert "Nenhuma linha de votação para 2022 turno 2" in _saida(r)


def test_turno_invalido(ambiente):
    r = CliRunner().invoke(app, _args(ambiente, 2022, 3))
    assert r.exit_code == 1
    assert "Turno 3 inválido" in _saida(r)
