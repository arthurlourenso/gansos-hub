"""Inicializa o banco gansos.db a partir do schema.sql.
Uso: python init_db.py [--force]
  --force  recria o banco mesmo que já exista (apaga tudo).
"""
import argparse
import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "db", "gansos.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "db", "schema.sql")


def init_db(force: bool = False) -> None:
    if force and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Banco anterior removido: {DB_PATH}")

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = f.read()

    with sqlite3.connect(DB_PATH) as con:
        con.executescript(schema)

    print(f"Banco inicializado: {DB_PATH}")

    # Verificação rápida: todas as tabelas esperadas existem
    esperadas = {"profissionais", "vendas", "categorias_produto", "parametros", "apuracoes"}
    with sqlite3.connect(DB_PATH) as con:
        existentes = {
            row[0]
            for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    faltando = esperadas - existentes
    if faltando:
        print(f"ERRO: tabelas ausentes após criação: {faltando}", file=sys.stderr)
        sys.exit(1)

    print(f"Tabelas OK: {', '.join(sorted(esperadas))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inicializa o banco Gansos Hub.")
    parser.add_argument("--force", action="store_true", help="Recria o banco do zero.")
    args = parser.parse_args()
    init_db(force=args.force)
