"""
scripts/migrar_vendas_supabase.py — Carga das vendas do SQLite local no Postgres (Supabase).

As tabelas pequenas (profissionais, parametros, apuracoes) já foram migradas via MCP.
Este script cuida só das ~25k vendas, que são muitas para passar pelo MCP.

Lê a string de conexão de .streamlit/secrets.toml (chave DATABASE_URL) ou da env var.
Idempotente: se as vendas já existem (mesmo total), não duplica.

Uso: python scripts/migrar_vendas_supabase.py
"""
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE = os.path.join(ROOT, "db", "gansos.db")


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    secrets = os.path.join(ROOT, ".streamlit", "secrets.toml")
    if os.path.exists(secrets):
        try:
            import tomllib
            with open(secrets, "rb") as f:
                data = tomllib.load(f)
            if data.get("DATABASE_URL"):
                return data["DATABASE_URL"]
        except Exception as e:
            print(f"Falha ao ler secrets.toml: {e}", file=sys.stderr)
    print("DATABASE_URL não encontrada (env var ou .streamlit/secrets.toml).", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    import psycopg2
    from psycopg2.extras import execute_values

    url = _database_url()
    sl = sqlite3.connect(SQLITE)
    sl.row_factory = sqlite3.Row
    cols = ["id", "data_hora", "valor", "tipo", "item", "profissional_id",
            "cliente", "comissao_sistema", "arquivo_origem", "importado_em"]
    rows = sl.execute(f"SELECT {','.join(cols)} FROM vendas ORDER BY id").fetchall()
    total_sqlite = len(rows)
    print(f"SQLite: {total_sqlite} vendas a migrar.")

    pg = psycopg2.connect(url)
    pg.autocommit = False
    cur = pg.cursor()

    cur.execute("SELECT COUNT(*) FROM vendas")
    ja = cur.fetchone()[0]
    if ja:
        print(f"Postgres já tem {ja} vendas. Abortando para não duplicar. "
              "Esvazie a tabela antes de recarregar, se for o caso.")
        pg.close(); sl.close()
        sys.exit(0)

    dados = [tuple(r[c] for c in cols) for r in rows]
    execute_values(
        cur,
        f"INSERT INTO vendas ({','.join(cols)}) VALUES %s",
        dados, page_size=1000,
    )
    cur.execute("SELECT setval(pg_get_serial_sequence('vendas','id'), (SELECT MAX(id) FROM vendas))")
    pg.commit()

    cur.execute("SELECT COUNT(*), ROUND(SUM(valor),2) FROM vendas")
    n, soma = cur.fetchone()
    print(f"Postgres após carga: {n} vendas, soma R${soma}.")
    print("OK — contagem bate." if n == total_sqlite else "ATENÇÃO — contagem divergente!")

    pg.close(); sl.close()


if __name__ == "__main__":
    main()
