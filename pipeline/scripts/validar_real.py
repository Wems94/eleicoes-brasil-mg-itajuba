"""Validação com dados reais do TSE: download + staging + marts de um ano.

Uso (de dentro de pipeline/):
    uv run python scripts/validar_real.py --ano 2022 --turnos 1 2

Grava num banco separado (data/validacao.duckdb) para não misturar com o oficial.
Os ZIPs ficam em data/raw/ e são reaproveitados numa segunda execução.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import time
from pathlib import Path

import duckdb

from eleicoes.config import DATA_DIR, RAW_DIR
from eleicoes.download import baixar_todas
from eleicoes.fontes import Catalogo
from eleicoes.lgpd import verificar_banco
from eleicoes.marts import construir_marts
from eleicoes.qualidade import executar
from eleicoes.staging import SemDados, carregar_particao

ESPACO_MINIMO_GB = 15


def _tabela(con: duckdb.DuckDBPyConnection, titulo: str, sql: str) -> None:
    print(f"\n## {titulo}")
    rel = con.sql(sql)
    print(" | ".join(rel.columns))
    for linha in rel.fetchall():
        print(" | ".join(f"{v:.2f}" if isinstance(v, float) else str(v) for v in linha))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--ano", type=int, default=2022)
    p.add_argument("--turnos", type=int, nargs="+", default=[1, 2])
    p.add_argument("--db", type=Path, default=DATA_DIR / "validacao.duckdb")
    p.add_argument("--raw", type=Path, default=RAW_DIR)
    p.add_argument("--base-url", help="sobrescreve a URL do TSE (testes)")
    p.add_argument("--forcar", action="store_true", help="baixa de novo mesmo se já existir")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args.raw.mkdir(parents=True, exist_ok=True)
    livre_gb = shutil.disk_usage(args.raw).free / 1e9
    if livre_gb < ESPACO_MINIMO_GB:
        logging.warning(
            "Só %.0f GB livres; a extração temporária dos CSVs pode passar de 10 GB", livre_gb
        )

    t0 = time.monotonic()
    catalogo = Catalogo.carregar(base_url=args.base_url)
    downloads = baixar_todas(catalogo.resolver(args.ano), args.raw, forcar=args.forcar)
    t_download = time.monotonic() - t0

    args.db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(args.db))
    carregados = []
    for turno in args.turnos:
        t = time.monotonic()
        try:
            r = carregar_particao(con, args.ano, turno, downloads, DATA_DIR / "trabalho")
        except SemDados as e:
            print(f"\nTurno {turno} pulado: {e}")
            continue
        carregados.append(turno)
        print(
            f"\nStaging {args.ano}/{turno} em {time.monotonic() - t:.0f}s — "
            f"Itajubá={r.cd_municipio}, fallback Presidente={r.fallback_presidente}, "
            f"fontes ausentes={r.fontes_ausentes or 'nenhuma'}"
        )
        for tabela, n in r.linhas.items():
            print(f"  {tabela:<18} {n:>12,} linhas")

    if not carregados:
        print("Nenhum turno com dados; nada a validar.")
        return 1

    t = time.monotonic()
    construir_marts(con)
    t_marts = time.monotonic() - t

    _tabela(
        con,
        "Presidente — Brasil",
        """SELECT turno, posicao, nm_urna_candidato, sg_partido, votos, pct_validos
           FROM marts.resultado_brasil WHERE posicao <= 3 ORDER BY turno, posicao""",
    )
    _tabela(
        con,
        "Comparecimento por UF (Presidente, 1º turno, 5 maiores colégios)",
        """SELECT sg_uf, aptos, comparecimento, pct_comparecimento, pct_brancos, pct_nulos
           FROM marts.comparecimento_uf WHERE cd_cargo = 1 AND turno = 1
           ORDER BY aptos DESC LIMIT 5""",
    )
    _tabela(
        con,
        "Itajubá — Presidente",
        """SELECT turno, tipo_votavel, nm_urna_candidato, sg_partido, votos, pct_validos
           FROM marts.itajuba_resultado WHERE cd_cargo = 1
           ORDER BY turno, tipo_votavel, votos DESC""",
    )
    _tabela(
        con,
        "Itajubá — volume por nível",
        """SELECT (SELECT count(DISTINCT (nr_zona, nr_secao)) FROM marts.itajuba_secao) secoes,
                  (SELECT count(DISTINCT nr_local_votacao) FROM marts.itajuba_local) locais,
                  (SELECT count(*) FROM marts.itajuba_local WHERE nr_latitude IS NULL) sem_coord""",
    )

    print("\n## Gate de qualidade (4.1)")
    ok = True
    for turno in carregados:
        relatorio = executar(con, args.ano, turno)
        print(relatorio.texto())
        ok = ok and relatorio.ok

    print("\n## Verificador LGPD (4.2)")
    vazamentos = verificar_banco(con)
    for v in vazamentos:
        print(f"  [ERRO] {v}")
    print("  [OK] nenhum dado pessoal encontrado" if not vazamentos else "")
    ok = ok and not vazamentos

    print(
        f"\nTempo: download {t_download:.0f}s, marts {t_marts:.0f}s, "
        f"total {time.monotonic() - t0:.0f}s. Banco: {args.db}"
    )
    con.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
