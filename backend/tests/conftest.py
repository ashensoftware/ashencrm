"""Postgres desechable por corrida de pruebas.

Cada sesión crea `crm_test_<aleatorio>`, aplica las mismas migraciones que
producción y la borra al final. Los pools por defecto y `settings` apuntan a
ese schema durante la sesión, así que ninguna prueba puede tocar `crm`.

URL: TEST_DATABASE_URL, si no DATABASE_ADMIN_URL, si no DATABASE_URL. El rol
necesita CREATE en la base (crear y borrar el schema). Sin URL, las pruebas
que usan la base se marcan como omitidas.
"""

from __future__ import annotations

import os
import secrets

import pytest

from backend.config.settings import settings

_URL = (
    os.getenv("TEST_DATABASE_URL")
    or os.getenv("DATABASE_ADMIN_URL")
    or os.getenv("DATABASE_URL")
    or ""
).strip()

_TABLES_TO_KEEP = {"schema_migrations"}


@pytest.fixture(scope="session")
def pg_pool():
    if not _URL:
        pytest.skip("Sin TEST_DATABASE_URL/DATABASE_URL: pruebas de Postgres omitidas")

    import psycopg

    from backend.api import app_factory
    from backend.infrastructure.persistence import pg
    from backend.infrastructure.persistence.migrate import run_migrations

    schema = f"crm_test_{secrets.token_hex(4)}"
    run_migrations(_URL, schema)
    pool = pg.make_pool(_URL, schema, min_size=1, max_size=4, name="ashencrm-test")

    saved = (settings.database_url, settings.database_readonly_url, settings.database_schema)
    settings.database_url, settings.database_readonly_url, settings.database_schema = _URL, "", schema
    pg.set_default_pools(pool)
    app_factory._migrated = True
    try:
        yield pool
    finally:
        pg.set_default_pools(None)
        pool.close()
        settings.database_url, settings.database_readonly_url, settings.database_schema = saved
        kwargs = pg.connection_kwargs(_URL)
        kwargs.pop("row_factory", None)
        with psycopg.connect(_URL, autocommit=True, **kwargs) as conn:
            conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")


@pytest.fixture()
def clean_db(pg_pool):
    """Vacía todas las tablas y restaura las categorías por defecto."""
    from backend.infrastructure.persistence.prospect_repository import DEFAULT_CATEGORIES

    with pg_pool.connection() as conn:
        tables = [
            r["relname"]
            for r in conn.execute(
                "SELECT c.relname FROM pg_class c "
                "WHERE c.relnamespace = current_schema()::regnamespace AND c.relkind = 'r'"
            ).fetchall()
            if r["relname"] not in _TABLES_TO_KEEP
        ]
        conn.execute(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE")
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO category_catalog (name, label, icon) VALUES (%s, %s, %s)",
                DEFAULT_CATEGORIES,
            )
    return pg_pool


@pytest.fixture()
def prospect_repo(clean_db):
    from backend.infrastructure.persistence.prospect_repository import ProspectRepository

    return ProspectRepository(pool=clean_db)


@pytest.fixture()
def platform_repo(clean_db):
    from backend.infrastructure.persistence.platform_repository import PlatformRepository

    return PlatformRepository(pool=clean_db)
