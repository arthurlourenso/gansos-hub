"""
src/db.py — Camada de conexão: SQLite local ou PostgreSQL (DATABASE_URL).
Uso: from src.db import conectar, mes_expr, date_expr
"""
import os
import sqlite3 as _sqlite3

_DATABASE_URL = os.environ.get("DATABASE_URL")
_SQLITE_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "gansos.db")


def dialect() -> str:
    return "postgres" if _DATABASE_URL else "sqlite"


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
        else:
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


def conectar(path: str | None = None) -> Connection:
    """Retorna uma Connection para PostgreSQL (se DATABASE_URL definida) ou SQLite."""
    if _DATABASE_URL:
        import psycopg2
        conn = psycopg2.connect(_DATABASE_URL)
        return Connection(conn, is_pg=True)
    db_path = path or _SQLITE_PATH
    conn = _sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = _sqlite3.Row
    return Connection(conn, is_pg=False)
