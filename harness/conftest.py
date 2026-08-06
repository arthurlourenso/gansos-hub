import json
import os
import sys

import pytest

HARNESS_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.dirname(HARNESS_DIR)
sys.path.insert(0, ROOT_DIR)

DB_PATH = os.path.join(ROOT_DIR, "db", "gansos.db")
GOLDEN_PATH = os.path.join(HARNESS_DIR, "golden_numbers.json")


@pytest.fixture(scope="session")
def con():
    assert os.path.exists(DB_PATH), f"Banco não encontrado: {DB_PATH}. Rode init_db.py + ingestao.py primeiro."
    import src.db as db
    c = db.conectar()
    yield c
    c.close()


@pytest.fixture(scope="session")
def golden():
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        return json.load(f)
