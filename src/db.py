"""
src/db.py — Camada de conexão: SQLite local ou PostgreSQL (Supabase).

Resolução da DATABASE_URL (nesta ordem):
  1. variável de ambiente DATABASE_URL (scripts, harness, CI).
  2. st.secrets["DATABASE_URL"] — SÓ quando rodando dentro do app Streamlit.
Caso contrário, SQLite local. Assim o app online usa Supabase e as ferramentas
de linha de comando seguem no SQLite local, salvo override explícito por env var.
"""
import os
import sqlite3 as _sqlite3

_SQLITE_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "gansos.db")

_url_cache = None
_url_resolvido = False


def _database_url() -> str | None:
    global _url_cache, _url_resolvido
    if _url_resolvido:
        return _url_cache
    url = os.environ.get("DATABASE_URL")
    if not url:
        try:
            import streamlit as st
            from streamlit.runtime import exists as _rt_exists
            if _rt_exists() and "DATABASE_URL" in st.secrets:
                url = st.secrets["DATABASE_URL"]
        except Exception:
            pass
    _url_cache = url
    _url_resolvido = True
    return url


def dialect() -> str:
    return "postgres" if _database_url() else "sqlite"


def mes_expr(col: str) -> str:
    """Expressão SQL para extrair YYYY-MM de uma coluna de data/hora."""
    if dialect() == "postgres":
        return f"to_char({col}, 'YYYY-MM')"
    return f"strftime('%Y-%m', {col})"


def date_expr(col: str) -> str:
    """Expressão SQL para extrair a data (YYYY-MM-DD) como texto."""
    if dialect() == "postgres":
        return f"({col}::date)::text"
    return f"date({col})"


class _Row:
    """Row com acesso por índice numérico e por nome de coluna."""
    __slots__ = ("_keys", "_vals")

    def __init__(self, raw):
        if isinstance(raw, _sqlite3.Row):
            self._keys = list(raw.keys())
            self._vals = tuple(raw)
        else:
            self._keys = list(raw.keys())
            self._vals = tuple(raw.values())

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._vals[key]
        return self._vals[self._keys.index(key)]

    def keys(self):
        return self._keys

    def __iter__(self):
        return iter(self._vals)

    def __repr__(self):
        return str(dict(zip(self._keys, self._vals)))


class _Cursor:
    def __init__(self, raw):
        self._raw = raw

    def fetchone(self):
        row = self._raw.fetchone()
        return _Row(row) if row is not None else None

    def fetchall(self):
        return [_Row(r) for r in self._raw.fetchall()]

    def __iter__(self):
        for r in self._raw:
            yield _Row(r)

    @property
    def lastrowid(self):
        return self._raw.lastrowid


class Connection:
    """Wrapper uniforme sobre sqlite3 e psycopg2."""

    def __init__(self, raw, is_pg: bool):
        self._conn = raw
        self._is_pg = is_pg

    @property
    def dialect(self) -> str:
        return "postgres" if self._is_pg else "sqlite"

    def execute(self, sql: str, params=()):
        if self._is_pg:
            from psycopg2.extras import RealDictCursor
            sql = sql.replace("?", "%s")
            cur = self._conn.cursor(cursor_factory=RealDictCursor)
            try:
                cur.execute(sql, params)
            except Exception:
                # No Postgres uma query com erro aborta a transação e envenena
                # a conexão (em cache) para todas as seguintes. Rollback mantém
                # a conexão utilizável, como no SQLite.
                self._conn.rollback()
                raise
            return _Cursor(cur)
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return _Cursor(cur)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        if exc_type is None:
            self.commit()
        self.close()


_decimal_registrado = False


def _registrar_decimal_como_float(psycopg2) -> None:
    """Faz NUMERIC do Postgres voltar como float, igual ao REAL do SQLite.

    Sem isso, SUM(valor) volta Decimal no Postgres e float no SQLite, e a
    apuração/relatórios divergem por tipo. A camada de abstração normaliza isso.
    """
    global _decimal_registrado
    if _decimal_registrado:
        return
    from psycopg2 import extensions
    dec2float = extensions.new_type(
        extensions.DECIMAL.values,
        "DEC2FLOAT",
        lambda value, curs: float(value) if value is not None else None,
    )
    extensions.register_type(dec2float)
    _decimal_registrado = True


def conectar(path: str | None = None) -> Connection:
    """Retorna uma Connection para PostgreSQL (se DATABASE_URL definida) ou SQLite."""
    url = _database_url()
    if url:
        import psycopg2
        _registrar_decimal_como_float(psycopg2)
        conn = psycopg2.connect(url)
        return Connection(conn, is_pg=True)
    db_path = path or _SQLITE_PATH
    conn = _sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.row_factory = _sqlite3.Row
    return Connection(conn, is_pg=False)
