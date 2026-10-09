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
from eleicoes.marts import construir_marts
from eleicoes.staging import SemDados, carregar_particao

ESPACO_MINIMO_GB = 15


def _tabela(con: duckdb.DuckDBPyConnection, titulo: str, sql: str) -> None:
    print(f"\n## {titulo}")
    rel = con.sql(sql)
    print(" | ".join(rel.columns))
    for linha in rel.fetchall():
        print(" | ".join(f"{v:.2f}" if isinstance(v, float) else str(v) for v in linha))


def _checagem(con: duckdb.DuckDBPyConnection, nome: str, sql: str) -> bool:
    (n,) = con.sql(sql).fetchone()
    print(f"  [{'OK ' if n == 0 else 'ERRO'}] {nome}: {n} divergência(s)")
    return n == 0


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

    print("\n## Checagens de consistência (prévia do gate de qualidade)")
    ok = all(
        [
            _checagem(
                con,
                "presidente nacional soma 100% dos válidos",
                """SELECT count(*) FROM (SELECT ano, turno, sum(pct_validos) s
                   FROM marts.resultado_brasil GROUP BY ALL) WHERE abs(s - 100) > 1e-6""",
            ),
            _checagem(
                con,
                "munzona: válidos + brancos + nulos + anulados + sub judice"
                " = comparecimento × votos/eleitor",
                """SELECT count(*) FROM staging.detalhe_munzona d
                   JOIN marts.cargos USING (ano, cd_cargo)
                   WHERE qt_votos_validos + qt_votos_brancos + qt_votos_nulos
                         + coalesce(qt_votos_anulados, 0)
                         + coalesce(qt_votos_anulados_subjudice, 0)
                         <> qt_comparecimento * votos_por_eleitor""",
            ),
            _checagem(
                con,
                "Itajubá: soma por seção = munzona, por candidato",
                """WITH s AS (SELECT ano, turno, cd_cargo, nr_votavel, sum(votos) v
                             FROM marts.itajuba_resultado WHERE tipo_votavel = 'candidato'
                             GROUP BY ALL),
                        m AS (SELECT ano, turno, cd_cargo, nr_candidato nr_votavel,
                                     sum(qt_votos_nominais) v
                              FROM staging.votacao_munzona
                              WHERE cd_municipio = (SELECT any_value(cd_municipio)
                                                    FROM staging.votacao_secao)
                              GROUP BY ALL)
                   SELECT count(*) FROM s FULL JOIN m USING (ano, turno, cd_cargo, nr_votavel)
                   WHERE s.v IS DISTINCT FROM m.v AND coalesce(m.v, 0) > 0""",
            ),
            _checagem(
                con,
                "nenhuma coluna de CPF/e-mail/nascimento/título no banco",
                """SELECT count(*) FROM information_schema.columns
                   WHERE regexp_matches(lower(column_name), 'cpf|email|nascimento|titulo')""",
            ),
        ]
    )

    print(
        f"\nTempo: download {t_download:.0f}s, marts {t_marts:.0f}s, "
        f"total {time.monotonic() - t0:.0f}s. Banco: {args.db}"
    )
    con.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
