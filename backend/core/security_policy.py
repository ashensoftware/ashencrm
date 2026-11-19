"""Política de arranque: CORS, consola SQL y envío de outreach.

Las funciones son puras para poder probarlas sin levantar FastAPI ni leer la base.
"""

from __future__ import annotations

LOCAL_ENVS = {"dev", "development", "local", "test", "testing"}
PRODUCTION_ENVS = {"prod", "production"}
PRODUCTION_SQL_ACK = "read-only-acknowledged"

LOCAL_DEFAULT_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
)


def is_local_env(app_env: str | None) -> bool:
    return (app_env or "").strip().lower() in LOCAL_ENVS


def is_production_env(app_env: str | None) -> bool:
    return (app_env or "").strip().lower() in PRODUCTION_ENVS


def env_flag(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def resolve_allowed_origins(app_env: str | None, raw: str | None) -> list[str]:
    """Orígenes CORS explícitos. El comodín '*' no es válido en ningún entorno."""
    text = (raw or "").strip()
    if not text:
        if is_local_env(app_env):
            return list(LOCAL_DEFAULT_ORIGINS)
        raise RuntimeError(
            "ALLOWED_ORIGINS es obligatorio fuera de development/test y no puede ser '*'"
        )
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if not parts or any(part == "*" for part in parts):
        raise RuntimeError("ALLOWED_ORIGINS no puede contener '*' ni quedar vacío")
    return parts


def resolve_sql_console_enabled(
    app_env: str | None,
    allow_raw: str | None,
    ack_raw: str | None,
) -> bool:
    """Por defecto apagada. En production hace falta un acuse explícito de solo lectura."""
    if not env_flag(allow_raw, False):
        return False
    if is_local_env(app_env):
        return True
    return (ack_raw or "").strip() == PRODUCTION_SQL_ACK


def outreach_is_live(app_env: str | None, enabled: bool) -> bool:
    """Solo production con el flag activo puede salir de dry-run.

    development, test y cualquier otro nombre de entorno quedan en dry-run
    aunque OUTREACH_ENABLED esté en true.
    """
    return is_production_env(app_env) and bool(enabled)


def legacy_maps_scraper_enabled(app_env: str | None, enabled: bool) -> bool:
    """El scraper DOM no puede activarse en production."""
    if is_production_env(app_env):
        return False
    return bool(enabled)


def browser_automation_enabled(app_env: str | None, enabled: bool) -> bool:
    """Playwright contra Lovable queda apagado en production y por defecto."""
    if is_production_env(app_env):
        return False
    return bool(enabled)


def assert_auth_mode(app_env: str | None, auth_mode: str | None) -> str:
    mode = (auth_mode or "").strip().lower()
    if mode not in {"local", "oidc"}:
        raise RuntimeError("AUTH_MODE debe ser 'local' u 'oidc'")
    if not is_local_env(app_env) and mode != "oidc":
        raise RuntimeError("Fuera de development/test AUTH_MODE debe ser oidc")
    return mode
