"""Decodificador de Boletim de Urna do TSE (ASN.1 BER), D9.

Segue a mesma navegação do decodificador de referência `scripts/bu_dump.py`:
envelope -> EntidadeBoletimUrna -> resultadosVotacaoPorEleicao -> cargos -> votos.
A identificação da seção vem do campo [3] (IdentificacaoSecaoEleitoral:
municipioZona{municipio, zona}, local, secao).

Uso: python -m eleicoes.bu <arquivo.bu|.dat>
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

CARGOS = {
    1: "Presidente",
    2: "Vice-Presidente",
    3: "Governador",
    4: "Vice-Governador",
    5: "Senador",
    6: "Deputado Federal",
    7: "Deputado Estadual",
    8: "Deputado Distrital",
}
TIPOS_VOTO = {
    1: "nominal",
    2: "branco",
    3: "nulo",
    4: "legenda",
    5: "cargo sem candidato",
    6: "nominal anulado",
    7: "legenda anulado",
}
# Votos que cada eleitor dá no cargo. Senador varia por ano (1 ou 2 vagas) e
# fica de fora: a regra de soma do Senado é aplicada no gate de qualidade.
VOTOS_POR_ELEITOR = {1: 1, 3: 1, 6: 1, 7: 1, 8: 1}

Tlv = tuple[int, "bytes | list[Tlv]"]


def _parse(b: bytes, i: int = 0, fim: int | None = None) -> list[Tlv]:
    fim = len(b) if fim is None else fim
    out: list[Tlv] = []
    while i < fim:
        tag = b[i]
        i += 1
        tam = b[i]
        i += 1
        if tam & 0x80:
            n = tam & 0x7F
            tam = int.from_bytes(b[i : i + n], "big")
            i += n
        valor = b[i : i + tam]
        out.append((tag, _parse(b, i, i + tam) if tag & 0x20 else valor))
        i += tam
    return out


def _int(v: bytes | list) -> int:
    assert isinstance(v, bytes)
    return int.from_bytes(v, "big", signed=True)


def _contexto(campos: list[Tlv]) -> dict[int, bytes | list[Tlv]]:
    """Campos com tag de contexto, indexados pelo número da tag."""
    return {t & 0x1F: v for t, v in campos if t & 0xC0 == 0x80}


@dataclass(frozen=True)
class Voto:
    tipo: str
    quantidade: int
    partido: int | None = None
    numero: int | None = None


@dataclass(frozen=True)
class Cargo:
    codigo: int
    ordem: int
    tipo_cargo: int
    comparecimento: int
    votos: tuple[Voto, ...]

    @property
    def nome(self) -> str:
        return CARGOS.get(self.codigo, str(self.codigo))

    @property
    def total(self) -> int:
        return sum(v.quantidade for v in self.votos)


@dataclass(frozen=True)
class Eleicao:
    id_eleicao: int
    aptos: int
    cargos: tuple[Cargo, ...]


@dataclass(frozen=True)
class Divergencia:
    cargo: str
    esperado: int
    total: int


@dataclass(frozen=True)
class BoletimUrna:
    municipio: int
    zona: int
    local: int
    secao: int
    eleicoes: tuple[Eleicao, ...] = field(default_factory=tuple)

    def cargos(self) -> list[Cargo]:
        return [c for e in self.eleicoes for c in e.cargos]

    def cargo(self, codigo: int) -> Cargo:
        return next(c for c in self.cargos() if c.codigo == codigo)

    def divergencias(self) -> list[Divergencia]:
        """Cargos cuja soma de votos difere de comparecimento × votos por eleitor."""
        return [
            Divergencia(c.nome, c.comparecimento * VOTOS_POR_ELEITOR[c.codigo], c.total)
            for c in self.cargos()
            if c.codigo in VOTOS_POR_ELEITOR
            and c.total != c.comparecimento * VOTOS_POR_ELEITOR[c.codigo]
        ]

    def votos_df(self) -> pl.DataFrame:
        linhas = [
            {
                "municipio": self.municipio,
                "zona": self.zona,
                "secao": self.secao,
                "id_eleicao": e.id_eleicao,
                "cd_cargo": c.codigo,
                "nm_cargo": c.nome,
                "tipo_voto": v.tipo,
                "nr_partido": v.partido,
                "nr_votavel": v.numero,
                "qt_votos": v.quantidade,
            }
            for e in self.eleicoes
            for c in e.cargos
            for v in c.votos
        ]
        return pl.DataFrame(
            linhas,
            schema={
                "municipio": pl.Int64,
                "zona": pl.Int64,
                "secao": pl.Int64,
                "id_eleicao": pl.Int64,
                "cd_cargo": pl.Int64,
                "nm_cargo": pl.String,
                "tipo_voto": pl.String,
                "nr_partido": pl.Int64,
                "nr_votavel": pl.Int64,
                "qt_votos": pl.Int64,
            },
        )


def _voto(campos: list[Tlv]) -> Voto:
    x = _contexto(campos)
    tipo = _int(x[1])
    partido = numero = None
    if 3 in x:
        ident = x[3]
        assert isinstance(ident, list)
        partido, numero = _int(ident[0][1]), _int(ident[1][1])
    return Voto(TIPOS_VOTO.get(tipo, str(tipo)), _int(x[2]), partido, numero)


def decodificar(dados: bytes) -> BoletimUrna:
    envelope = _parse(dados)[0][1]
    bu = _parse(envelope[4][1])[0][1]

    ident = _contexto(bu[3][1])
    mun_zona = _contexto(ident[0])

    eleicoes = []
    for _, f in bu[8][1]:
        cargos = []
        for _, r in f[4][1]:
            tipo_cargo, comparecimento = _int(r[0][1]), _int(r[1][1])
            for _, c in r[2][1]:
                cargos.append(
                    Cargo(
                        codigo=_int(c[0][1]),
                        ordem=_int(c[1][1]),
                        tipo_cargo=tipo_cargo,
                        comparecimento=comparecimento,
                        votos=tuple(_voto(vv) for _, vv in c[2][1]),
                    )
                )
        eleicoes.append(Eleicao(_int(f[0][1]), _int(f[1][1]), tuple(cargos)))

    return BoletimUrna(
        municipio=_int(mun_zona[0]),
        zona=_int(mun_zona[1]),
        local=_int(ident[1]),
        secao=_int(ident[2]),
        eleicoes=tuple(eleicoes),
    )


def ler(path: Path) -> BoletimUrna:
    return decodificar(Path(path).read_bytes())


def main(argv: list[str] | None = None) -> None:
    for arquivo in argv if argv is not None else sys.argv[1:]:
        bu = ler(Path(arquivo))
        print(f"# {arquivo}: município {bu.municipio}, zona {bu.zona}, seção {bu.secao}")
        for c in bu.cargos():
            print(f"  {c.nome}: comparecimento {c.comparecimento}, total {c.total}")
        for d in bu.divergencias():
            print(f"  DIVERGÊNCIA {d.cargo}: esperado {d.esperado}, total {d.total}")


if __name__ == "__main__":
    main()
