"""Inicializa o banco a partir do schema adequado (SQLite local ou PostgreSQL).
Uso: python init_db.py [--force]
  --force  recria as tabelas (DROP + CREATE) — PostgreSQL; apaga o .db — SQLite.
"""
import argparse
import os
import sys

ROOT_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(ROOT_DIR, "db", "gansos.db")
SCHEMA_SQLITE = os.path.join(ROOT_DIR, "db", "schema.sql")
SCHEMA_PG = os.path.join(ROOT_DIR, "db", "schema_pg.sql")

TABELAS = {"profissionais", "vendas", "categorias_produto", "parametros", "apuracoes"}


def _tabelas_existentes(con) -> set:
    d = con.dialect
    if d == "postgres":
        rows = con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        ).fetchall()
        return {r[0] for r in rows}
    rows = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {r[0] for r in rows}


def init_db(force: bool = False) -> None:
    import src.db as db

    if db.dialect() == "sqlite":
        if force and os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            print(f"Banco anterior removido: {DB_PATH}")
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

        import sqlite3
        with open(SCHEMA_SQLITE, encoding="utf-8") as f:
            schema = f.read()
        with sqlite3.connect(DB_PATH) as raw:
            raw.executescript(schema)
        print(f"Banco SQLite inicializado: {DB_PATH}")

    else:
        with open(SCHEMA_PG, encoding="utf-8") as f:
            schema = f.read()
        with db.conectar() as con:
            if force:
                for t in reversed(list(TABELAS)):
                    con.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
            for stmt in schema.split(";"):
                stmt = stmt.strip()
                if stmt and not stmt.startswith("--"):
                    con.execute(stmt)
        print("Banco PostgreSQL inicializado.")

    # Verificação
    with db.conectar() as con:
        existentes = _tabelas_existentes(con)
    faltando = TABELAS - existentes
    if faltando:
        print(f"ERRO: tabelas ausentes: {faltando}", file=sys.stderr)
        sys.exit(1)
    print(f"Tabelas OK: {', '.join(sorted(TABELAS))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inicializa o banco Gansos Hub.")
    parser.add_argument("--force", action="store_true", help="Recria o banco do zero.")
    args = parser.parse_args()
    init_db(force=args.force)
