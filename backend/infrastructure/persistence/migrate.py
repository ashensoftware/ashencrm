"""Migraciones SQL numeradas (`migrations/NNNN_nombre.sql`).

Todas las pendientes se aplican en una sola transacción, bajo un advisory lock,
así que dos procesos que arrancan a la vez no se pisan y un fallo no deja el
schema a medias. Los archivos no califican el schema: el runner fija
`search_path` al schema destino (`crm` en producción, `crm_test_*` en pruebas).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import psycopg

from backend.infrastructure.persistence.pg import connection_kwargs, validate_schema_name

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_NAME_RE = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")
_LOCK_KEY = 7_401_302_115  # constante arbitraria, única para ashencrm


def migration_files() -> list[Path]:
    files = sorted(p for p in MIGRATIONS_DIR.glob("*.sql") if _NAME_RE.match(p.name))
    versions = [p.name[:4] for p in files]
    if len(versions) != len(set(versions)):
        raise RuntimeError("Hay dos migraciones con el mismo número")
    return files


def run_migrations(url: str, schema: str) -> list[str]:
    """Aplica las migraciones pendientes. Devuelve los nombres aplicados."""
    validate_schema_name(schema)
    kwargs = connection_kwargs(url)
    kwargs.pop("row_factory", None)
    applied_now: list[str] = []
    with psycopg.connect(url, **kwargs) as conn:
        with conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (_LOCK_KEY,))
            # IF NOT EXISTS igual exige CREATE en la base; crm_app no lo tiene.
            exists = conn.execute(
                "SELECT 1 FROM pg_namespace WHERE nspname = %s", (schema,)
            ).fetchone()
            if not exists:
                conn.execute(f"CREATE SCHEMA {schema}")
            conn.execute(f"SET LOCAL search_path TO {schema}")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            done = {
                row[0]: row[1]
                for row in conn.execute("SELECT version, checksum FROM schema_migrations")
            }
            for path in migration_files():
                version = path.name[:4]
                body = path.read_text(encoding="utf-8")
                checksum = hashlib.sha256(body.encode("utf-8")).hexdigest()
                if version in done:
                    if done[version] != checksum:
                        raise RuntimeError(
                            f"La migración {path.name} cambió después de aplicarse. "
                            "Crea una migración nueva en vez de editarla."
                        )
                    continue
                conn.execute(body)
                conn.execute(
                    "INSERT INTO schema_migrations (version, name, checksum) VALUES (%s, %s, %s)",
                    (version, path.name, checksum),
                )
                applied_now.append(path.name)
    return applied_now


def main() -> None:
    from backend.config.settings import settings

    applied = run_migrations(settings.database_url, settings.database_schema)
    print("Aplicadas:", ", ".join(applied) if applied else "ninguna (al día)")


if __name__ == "__main__":
    main()
