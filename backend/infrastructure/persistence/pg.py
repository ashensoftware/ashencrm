"""Postgres connection pools (psycopg 3).

Every pooled connection:
- requires TLS unless the host is local (sslmode=require),
- uses `search_path = <schema>` so repository SQL stays unqualified,
- uses the business time zone, so naive ISO strings written by the app are read
  as Medellín local time, and timestamps come back with an explicit offset,
- returns rows as dicts with datetimes already converted to ISO strings, which
  keeps the API contract the SQLite version had (strings, not datetime objects).
"""

from __future__ import annotations

import re
import threading
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Sequence
from urllib.parse import urlsplit

from psycopg import Connection, Cursor
from psycopg.rows import RowMaker, dict_row
from psycopg_pool import ConnectionPool

BUSINESS_TIME_ZONE = "America/Bogota"
_SCHEMA_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres"}


def validate_schema_name(schema: str) -> str:
    if not _SCHEMA_RE.match(schema or ""):
        raise ValueError(f"Nombre de schema inválido: {schema!r}")
    return schema


def to_api_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, memoryview):
        return bytes(value).decode("utf-8", errors="replace")
    return value


def api_dict_row(cursor: Cursor[Any]) -> RowMaker[dict[str, Any]]:
    make = dict_row(cursor)

    def row(values: Sequence[Any]) -> dict[str, Any]:
        data = make(values)
        for key, value in data.items():
            if isinstance(value, (datetime, date, Decimal, memoryview)):
                data[key] = to_api_value(value)
        return data

    return row


def connection_kwargs(url: str) -> dict[str, Any]:
    host = (urlsplit(url).hostname or "").lower()
    kwargs: dict[str, Any] = {"row_factory": api_dict_row, "connect_timeout": 10}
    if host not in _LOCAL_HOSTS:
        kwargs["sslmode"] = "require"
    return kwargs


def _configure(schema: str):
    def configure(conn: Connection[Any]) -> None:
        conn.execute(f"SET search_path TO {schema}")
        conn.execute(f"SET TIME ZONE '{BUSINESS_TIME_ZONE}'")
        conn.commit()

    return configure


def make_pool(
    url: str,
    schema: str,
    *,
    min_size: int = 1,
    max_size: int = 5,
    name: str = "ashencrm",
) -> ConnectionPool:
    if not url:
        raise RuntimeError("DATABASE_URL no está configurada")
    validate_schema_name(schema)
    pool = ConnectionPool(
        url,
        kwargs=connection_kwargs(url),
        configure=_configure(schema),
        min_size=min_size,
        max_size=max_size,
        name=name,
        open=False,
        # Supavisor cierra conexiones ociosas; se reciclan antes.
        max_idle=300,
        max_lifetime=1800,
        timeout=15,
    )
    pool.open(wait=True, timeout=30)
    return pool


_lock = threading.Lock()
_default_pool: ConnectionPool | None = None
_readonly_pool: ConnectionPool | None = None


def get_default_pool() -> ConnectionPool:
    """Pool principal (rol crm_app). Se crea una vez por proceso."""
    global _default_pool
    with _lock:
        if _default_pool is None:
            from backend.config.settings import settings

            _default_pool = make_pool(settings.database_url, settings.database_schema)
        return _default_pool


def get_readonly_pool() -> ConnectionPool | None:
    """Pool del rol crm_readonly para la consola SQL. None si no está configurado."""
    global _readonly_pool
    with _lock:
        if _readonly_pool is None:
            from backend.config.settings import settings

            if not settings.database_readonly_url:
                return None
            _readonly_pool = make_pool(
                settings.database_readonly_url,
                settings.database_schema,
                min_size=0,
                max_size=2,
                name="ashencrm-readonly",
            )
        return _readonly_pool


def set_default_pools(main: ConnectionPool | None, readonly: ConnectionPool | None = None) -> None:
    """Pruebas: apunta los pools por defecto a un schema desechable."""
    global _default_pool, _readonly_pool
    with _lock:
        _default_pool = main
        _readonly_pool = readonly


def close_default_pools() -> None:
    global _default_pool, _readonly_pool
    with _lock:
        for pool in (_default_pool, _readonly_pool):
            if pool is not None:
                pool.close()
        _default_pool = None
        _readonly_pool = None
