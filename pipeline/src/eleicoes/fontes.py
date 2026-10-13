"""Catálogo de fontes do TSE e do IBGE (`config/fontes.yaml`) e resolução de URLs por ano."""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import yaml

from eleicoes.config import CONFIG_DIR

FONTES_PATH = CONFIG_DIR / "fontes.yaml"


class AnoNaoSuportado(ValueError):
    pass


@dataclass(frozen=True)
class Fonte:
    """Um arquivo do TSE ou do IBGE já resolvido para um ano."""

    nome: str
    ano: int
    descricao: str
    url: str
    membros: tuple[str, ...]
    excluir: tuple[str, ...]
    obrigatoria: bool
    # caminho relativo à URL base (o servidor de testes publica os arquivos por ele)
    caminho: str = ""
    formato: str = "zip"
    nome_arquivo: str | None = None

    @property
    def arquivo(self) -> str:
        return self.nome_arquivo or self.url.rsplit("/", 1)[1]

    def selecionar_membros(self, nomes: list[str]) -> list[str]:
        """Filtra os nomes de membros de um ZIP, preservando a ordem."""
        return [
            n
            for n in nomes
            if any(fnmatch(n, p) for p in self.membros)
            and not any(fnmatch(n, p) for p in self.excluir)
        ]


def _barra(url: str) -> str:
    return url if url.endswith("/") else url + "/"


@dataclass(frozen=True)
class Catalogo:
    bases: dict[str, str]
    anos: tuple[int, ...]
    fontes: dict[str, dict[str, Any]]

    @classmethod
    def carregar(cls, path: Path = FONTES_PATH, *, base_url: str | None = None) -> Catalogo:
        """`base_url` substitui todas as bases (servidor local nos testes)."""
        dados = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls(
            bases={k: _barra(base_url or v) for k, v in dados["bases"].items()},
            anos=tuple(dados["anos"]),
            fontes=dados["fontes"],
        )

    @property
    def base_url(self) -> str:
        return self.bases["tse"]

    def validar_ano(self, ano: int) -> None:
        if ano not in self.anos:
            suportados = ", ".join(str(a) for a in self.anos)
            raise AnoNaoSuportado(f"Ano {ano} não suportado. Anos suportados: {suportados}.")

    def fonte(self, nome: str, ano: int) -> Fonte:
        self.validar_ano(ano)
        spec = self.fontes[nome]
        caminho = spec["url"].format(ano=ano)
        return Fonte(
            nome=nome,
            ano=ano,
            descricao=spec.get("descricao", ""),
            url=self.bases[spec.get("base", "tse")] + caminho,
            membros=tuple(m.format(ano=ano) for m in spec.get("membros", ())),
            excluir=tuple(spec.get("excluir", ())),
            obrigatoria=bool(spec["obrigatoria"]),
            caminho=caminho,
            formato=spec.get("formato", "zip"),
            nome_arquivo=spec.get("arquivo"),
        )

    def resolver(self, ano: int) -> list[Fonte]:
        self.validar_ano(ano)
        return [self.fonte(nome, ano) for nome in self.fontes]
