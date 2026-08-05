"""H4 — Integridade contínua."""
import os
import sqlite3
import sys

import pytest

ROOT_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT_DIR)
from src.ingestao import importar

ARQUIVO_TESTE = os.path.join(ROOT_DIR, "dados", "entrada", "janeiro-26.xlsx")


def test_h4_dedup_reimportacao(con, golden):
    """Reimportar arquivo já importado deve inserir 0 linhas."""
    resultado = importar(ARQUIVO_TESTE, con)
    esperado = golden["H4"]["dedup_arquivo_inseridas"]
    assert resultado["inseridas"] == esperado, (
        f"Reimportação de janeiro-26.xlsx: esperado {esperado} inseridas, "
        f"obtido {resultado['inseridas']}"
    )


def test_h4_pendente_nao_entra_apuracao(con, golden):
    """Profissional 'pendente' não deve ter linhas em apuracoes."""
    pendentes_em_apuracao = con.execute("""
        SELECT COUNT(*) FROM apuracoes a
        WHERE json_extract(a.payload_json, '$.pendentes_incluidos') = 1
    """).fetchone()[0]
    assert pendentes_em_apuracao == 0, (
        f"{pendentes_em_apuracao} apuração(ões) com pendentes incluídos"
    )
