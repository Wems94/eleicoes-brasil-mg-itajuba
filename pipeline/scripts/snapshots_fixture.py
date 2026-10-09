"""Gera snapshots a partir dos fixtures dos testes (dados fictícios), para o build
e os testes do site sem depender de dados reais.

Uso (de dentro de pipeline/): uv run python scripts/snapshots_fixture.py ../web/.snapshots-fixture
"""

import sys
import tempfile
from pathlib import Path

import duckdb

from eleicoes.marts import construir_marts
from eleicoes.snapshots import gerar_snapshots
from eleicoes.staging import carregar_particao

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pacote tests/ (fixtures)
from tests.conftest import montar_zips  # noqa: E402


def main(destino: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        con = duckdb.connect(str(base / "eleicoes.duckdb"))
        z2022 = montar_zips(2022, base / "raw" / "2022")
        carregar_particao(con, 2018, 1, montar_zips(2018, base / "raw" / "2018"), base / "t")
        carregar_particao(con, 2022, 1, z2022, base / "t")
        carregar_particao(con, 2022, 2, z2022, base / "t")
        construir_marts(con)
        m = gerar_snapshots(con, destino, gerado_em="2026-10-09T20:00:00+00:00")
        con.close()
    print(f"{len(m['arquivos'])} snapshots de fixture em {destino}")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
