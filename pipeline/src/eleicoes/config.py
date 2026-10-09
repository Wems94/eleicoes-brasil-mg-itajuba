"""Caminhos padrão do pipeline (relativos a `pipeline/`)."""

import os
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = PIPELINE_DIR / "config"
DATA_DIR = Path(os.environ.get("ELEICOES_DATA_DIR", PIPELINE_DIR / "data"))
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "eleicoes.duckdb"
WEB_DATA_DIR = PIPELINE_DIR.parent / "web" / "data"
