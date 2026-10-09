import zipfile
from collections.abc import Callable, Iterable
from pathlib import Path

import duckdb
import pytest

from eleicoes.download import ResultadoDownload
from eleicoes.fontes import Catalogo

TSE = Path(__file__).parent / "fixtures" / "tse"


def montar_zips(
    ano: int,
    destino: Path,
    *,
    sem: Iterable[str] = (),
    substituir: dict[str, bytes] | None = None,
) -> dict[str, ResultadoDownload]:
    """Empacota os CSVs de `fixtures/tse/<ano>` como os ZIPs do TSE.

    ZIPs com vários membros ganham um `_BRASIL.csv` (união de todos), como no
    portal real, para provar que ele é ignorado. `sem` simula fontes opcionais
    ausentes; `substituir` troca o conteúdo de um membro pelo nome.
    """
    destino.mkdir(parents=True, exist_ok=True)
    substituir = substituir or {}
    csvs = sorted((TSE / str(ano)).glob("*.csv"))
    out = {}
    for fonte in Catalogo.carregar().resolver(ano):
        if fonte.nome in sem:
            out[fonte.nome] = ResultadoDownload(fonte, None, None, baixado=False)
            continue
        stem = fonte.arquivo.removesuffix(".zip")
        membros = {
            c.name: substituir.get(c.name, c.read_bytes()) for c in csvs if c.name.startswith(stem)
        }
        caminho = destino / fonte.arquivo
        with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as z:
            for nome, corpo in membros.items():
                z.writestr(nome, corpo)
            if len(membros) > 1:
                corpos = list(membros.values())
                cabecalho = corpos[0].split(b"\n", 1)[0]
                uniao = b"".join(c.split(b"\n", 1)[1] for c in corpos)
                z.writestr(f"{stem}_BRASIL.csv", cabecalho + b"\n" + uniao)
            z.writestr("leiame.pdf", b"%PDF-1.4")
        out[fonte.nome] = ResultadoDownload(fonte, caminho, None, baixado=True)
    return out


@pytest.fixture
def zips(tmp_path) -> Callable[..., dict[str, ResultadoDownload]]:
    def _zips(ano: int = 2022, **kwargs) -> dict[str, ResultadoDownload]:
        return montar_zips(ano, tmp_path / "raw" / str(ano), **kwargs)

    return _zips


@pytest.fixture
def con(tmp_path):
    c = duckdb.connect(str(tmp_path / "eleicoes.duckdb"))
    yield c
    c.close()


@pytest.fixture
def trabalho(tmp_path) -> Path:
    p = tmp_path / "trabalho"
    p.mkdir()
    return p


@pytest.fixture(scope="session")
def banco_completo(tmp_path_factory) -> Path:
    """Banco válido com 2018/1, 2022/1 e 2022/2 (staging + marts), somente leitura.

    Testes que alteram o banco devem trabalhar numa cópia.
    """
    from eleicoes.marts import construir_marts
    from eleicoes.staging import carregar_particao

    base = tmp_path_factory.mktemp("banco_completo")
    caminho = base / "eleicoes.duckdb"
    con = duckdb.connect(str(caminho))
    z2022 = montar_zips(2022, base / "raw" / "2022")
    carregar_particao(con, 2018, 1, montar_zips(2018, base / "raw" / "2018"), base / "t")
    carregar_particao(con, 2022, 1, z2022, base / "t")
    carregar_particao(con, 2022, 2, z2022, base / "t")
    construir_marts(con)
    con.close()
    return caminho
