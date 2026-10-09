"""Servidor HTTP local para os testes de download."""

from __future__ import annotations

import threading
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


@dataclass
class EstadoServidor:
    arquivos: dict[str, bytes] = field(default_factory=dict)
    # caminho -> quantas respostas seguidas serão cortadas no meio do corpo
    cortes: Counter[str] = field(default_factory=Counter)
    # caminho -> quantas respostas seguidas serão 503
    indisponivel: Counter[str] = field(default_factory=Counter)
    requisicoes: Counter[str] = field(default_factory=Counter)
    base_url: str = ""


def _handler(estado: EstadoServidor) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:  # silencia o stderr
            pass

        def do_GET(self) -> None:
            caminho = self.path.lstrip("/")
            estado.requisicoes[caminho] += 1
            if estado.indisponivel[caminho] > 0:
                estado.indisponivel[caminho] -= 1
                self.send_error(503)
                return
            corpo = estado.arquivos.get(caminho)
            if corpo is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            if estado.cortes[caminho] > 0:
                estado.cortes[caminho] -= 1
                self.wfile.write(corpo[: len(corpo) // 2])
                self.wfile.flush()
                self.close_connection = True
                return
            self.wfile.write(corpo)

    return Handler


@contextmanager
def servidor_http() -> Iterator[EstadoServidor]:
    estado = EstadoServidor()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _handler(estado))
    estado.base_url = f"http://127.0.0.1:{srv.server_address[1]}/"
    t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    t.start()
    try:
        yield estado
    finally:
        srv.shutdown()
        srv.server_close()
