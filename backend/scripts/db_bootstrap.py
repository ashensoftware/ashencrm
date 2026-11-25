"""Preparación única de Supabase Postgres (data-platform D3). Se ejecuta con el rol `postgres`.

1. Crea los roles crm_app (dueño del schema), crm_readonly (consola SQL, 5 s,
   solo lectura) y crm_ingest (scripts locales: sin DELETE) con contraseñas
   generadas aquí. Nunca se imprimen.
2. Borra las 10 tablas de plataforma que se aplicaron a mano en `public`
   (decisión 2026-11-20: SQLite es la fuente de verdad).
3. Crea el schema `crm` con dueño crm_app y aplica las migraciones como crm_app.
4. Escribe DATABASE_URL / DATABASE_READONLY_URL / DATABASE_INGEST_URL en .env
   y mueve la URL de postgres a DATABASE_ADMIN_URL. Copia previa en .env.bak.

Si los roles ya existen no cambia contraseñas salvo con --rotate.

Uso: python -m backend.scripts.db_bootstrap [--rotate] [--yes]
"""

from __future__ import annotations

import argparse
import secrets
import shutil
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
from dotenv import dotenv_values
from psycopg import sql

from backend.infrastructure.persistence.migrate import run_migrations
from backend.infrastructure.persistence.pg import connection_kwargs

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
SCHEMA = "crm"
LEGACY_PUBLIC_TABLES = (
    "pipeline_events",
    "pipeline_steps",
    "pipeline_runs",
    "field_observations",
    "businesses",
    "provider_connections",
    "suppression_entries",
    "outreach_consents",
    "outreach_messages",
    "audit_log",
)
ROLES = {
    # rol: (variable .env, ajustes de sesión)
    "crm_app": ("DATABASE_URL", {"search_path": SCHEMA}),
    "crm_readonly": (
        "DATABASE_READONLY_URL",
        {"search_path": SCHEMA, "statement_timeout": "5s", "default_transaction_read_only": "on"},
    ),
    "crm_ingest": ("DATABASE_INGEST_URL", {"search_path": SCHEMA, "statement_timeout": "60s"}),
}


def _role_url(admin_url: str, role: str, password: str) -> str:
    parts = urlsplit(admin_url)
    user = parts.username or ""
    # El pooler de Supabase identifica el proyecto por el sufijo: postgres.<ref>
    tenant = user.split(".", 1)[1] if "." in user else ""
    login = f"{role}.{tenant}" if tenant else role
    netloc = f"{quote(login, safe='.')}:{quote(password, safe='')}@{parts.hostname}"
    if parts.port:
        netloc += f":{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _write_env(updates: dict[str, str]) -> None:
    shutil.copy2(ENV_PATH, ENV_PATH.with_name(".env.bak"))
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else None
        if key in updates:
            if key not in seen:
                out.append(f"{key}={updates[key]}")
                seen.add(key)
            continue
        out.append(line)
    missing = [k for k in updates if k not in seen]
    if missing:
        out.append("")
        out.append("# Postgres (Supabase, pooler modo sesión). Generado por backend/scripts/db_bootstrap.py")
        out.extend(f"{k}={updates[k]}" for k in missing)
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rotate", action="store_true", help="Genera contraseñas nuevas aunque los roles existan")
    parser.add_argument("--yes", action="store_true", help="No pedir confirmación")
    args = parser.parse_args()

    env = dotenv_values(ENV_PATH)
    admin_url = (env.get("DATABASE_ADMIN_URL") or "").strip()
    if not admin_url:
        candidate = (env.get("DATABASE_URL") or "").strip()
        if (urlsplit(candidate).username or "").split(".")[0] != "postgres":
            print("Falta DATABASE_ADMIN_URL (o DATABASE_URL con el usuario postgres) en .env")
            return 2
        admin_url = candidate

    if not args.yes:
        answer = input(
            f"Esto borra {len(LEGACY_PUBLIC_TABLES)} tablas de public, crea roles y el schema {SCHEMA}. ¿Seguir? [s/N] "
        )
        if answer.strip().lower() not in {"s", "si", "sí", "y", "yes"}:
            return 1

    kwargs = connection_kwargs(admin_url)
    kwargs.pop("row_factory", None)
    passwords: dict[str, str] = {}
    with psycopg.connect(admin_url, **kwargs) as conn:
        with conn.transaction():
            existing = {
                r[0]
                for r in conn.execute(
                    "SELECT rolname FROM pg_roles WHERE rolname = ANY(%s)", (list(ROLES),)
                )
            }
            if existing and not args.rotate and existing != set(ROLES):
                print(f"Roles a medias ({sorted(existing)}). Usa --rotate para completarlos.")
                return 2
            for role, (_, settings_) in ROLES.items():
                ident = sql.Identifier(role)
                if role not in existing:
                    password = secrets.token_hex(24)
                    conn.execute(
                        sql.SQL(
                            "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION "
                            "NOBYPASSRLS PASSWORD {}"
                        ).format(ident, sql.Literal(password))
                    )
                    passwords[role] = password
                elif args.rotate:
                    password = secrets.token_hex(24)
                    conn.execute(
                        sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(ident, sql.Literal(password))
                    )
                    passwords[role] = password
                for name, value in settings_.items():
                    conn.execute(
                        sql.SQL("ALTER ROLE {} SET {} = {}").format(
                            ident, sql.Identifier(name), sql.Literal(value)
                        )
                    )
            # postgres debe poder crear el schema a nombre de crm_app.
            conn.execute("GRANT crm_app TO postgres")
            for table in LEGACY_PUBLIC_TABLES:
                conn.execute(
                    sql.SQL("DROP TABLE IF EXISTS {}.{} CASCADE").format(
                        sql.Identifier("public"), sql.Identifier(table)
                    )
                )
            conn.execute(
                sql.SQL("CREATE SCHEMA IF NOT EXISTS {} AUTHORIZATION crm_app").format(
                    sql.Identifier(SCHEMA)
                )
            )
            conn.execute(sql.SQL("REVOKE ALL ON SCHEMA {} FROM PUBLIC").format(sql.Identifier(SCHEMA)))

    if not passwords:
        app_url = (env.get("DATABASE_URL") or "").strip()
        if (urlsplit(app_url).username or "").split(".")[0] != "crm_app":
            print("Los roles ya existen y .env no tiene su URL. Ejecuta con --rotate.")
            return 2
    else:
        updates = {"DATABASE_ADMIN_URL": admin_url}
        for role, password in passwords.items():
            updates[ROLES[role][0]] = _role_url(admin_url, role, password)
        _write_env(updates)
        print(f"Roles con contraseña nueva: {', '.join(sorted(passwords))}. URLs escritas en .env (copia en .env.bak).")

    app_url = (dotenv_values(ENV_PATH).get("DATABASE_URL") or "").strip()
    applied = run_migrations(app_url, SCHEMA)
    print("Migraciones aplicadas como crm_app:", ", ".join(applied) if applied else "ninguna (al día)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
