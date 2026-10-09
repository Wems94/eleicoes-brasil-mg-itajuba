"""Catálogo de fontes do TSE (`config/fontes.yaml`) e resolução de URLs por ano."""

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
    """Um arquivo do TSE já resolvido para um ano."""

    nome: str
    ano: int
    descricao: str
    url: str
    membros: tuple[str, ...]
    excluir: tuple[str, ...]
    obrigatoria: bool

    @property
    def arquivo(self) -> str:
        return self.url.rsplit("/", 1)[1]

    def selecionar_membros(self, nomes: list[str]) -> list[str]:
        """Filtra os nomes de membros de um ZIP, preservando a ordem."""
        return [
            n
            for n in nomes
            if any(fnmatch(n, p) for p in self.membros)
            and not any(fnmatch(n, p) for p in self.excluir)
        ]


@dataclass(frozen=True)
class Catalogo:
    base_url: str
    anos: tuple[int, ...]
    fontes: dict[str, dict[str, Any]]

    @classmethod
    def carregar(cls, path: Path = FONTES_PATH, *, base_url: str | None = None) -> Catalogo:
        dados = yaml.safe_load(path.read_text(encoding="utf-8"))
        base = base_url or dados["base_url"]
        return cls(
            base_url=base if base.endswith("/") else base + "/",
            anos=tuple(dados["anos"]),
            fontes=dados["fontes"],
        )

    def validar_ano(self, ano: int) -> None:
        if ano not in self.anos:
            suportados = ", ".join(str(a) for a in self.anos)
            raise AnoNaoSuportado(f"Ano {ano} não suportado. Anos suportados: {suportados}.")

    def fonte(self, nome: str, ano: int) -> Fonte:
        self.validar_ano(ano)
        spec = self.fontes[nome]
        return Fonte(
            nome=nome,
            ano=ano,
            descricao=spec.get("descricao", ""),
            url=self.base_url + spec["url"].format(ano=ano),
            membros=tuple(m.format(ano=ano) for m in spec["membros"]),
            excluir=tuple(spec.get("excluir", ())),
            obrigatoria=bool(spec["obrigatoria"]),
        )

    def resolver(self, ano: int) -> list[Fonte]:
        self.validar_ano(ano)
        return [self.fonte(nome, ano) for nome in self.fontes]
