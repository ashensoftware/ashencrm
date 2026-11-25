"""Construcción de la app FastAPI con la política de seguridad de la iteración 1."""

from __future__ import annotations

import sys
import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.authorization import ApiAccessMiddleware
from backend.api.routes.admin import create_admin_router
from backend.api.routes.auth import create_auth_router
from backend.api.routes.catalog import create_catalog_router
from backend.api.routes.clients import create_clients_router
from backend.api.routes.demos import create_demo_router
from backend.api.routes.pipeline import create_pipeline_router
from backend.api.routes.prospects import create_prospects_router
from backend.api.routes.providers import create_provider_router
from backend.api.routes.scrape import create_scrape_router
from backend.api.routes.screenshots import router as screenshots_router
from backend.config.settings import settings
from backend.core import config
from backend.core.auth import HttpJwkProvider, TokenAuthenticator
from backend.core.security_policy import assert_auth_mode
from backend.database.db import Database
from backend.infrastructure.persistence.migrate import run_migrations
from backend.infrastructure.persistence.platform_repository import PlatformRepository
from backend.services.scrape_service import ScrapeService
from backend.workers.runner import worker_loop

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


@dataclass(frozen=True)
class RuntimeSecurity:
    app_env: str
    allowed_origins: tuple[str, ...]
    sql_console_enabled: bool
    outreach_enabled: bool
    auth_mode: str
    auth_local_secret: str = ""
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""


def runtime_security_from_settings() -> RuntimeSecurity:
    if settings.security_error:
        raise RuntimeError(settings.security_error)
    mode = assert_auth_mode(settings.app_env, settings.auth_mode)
    return RuntimeSecurity(
        app_env=settings.app_env,
        allowed_origins=tuple(settings.allowed_origins),
        sql_console_enabled=settings.sql_console_enabled,
        outreach_enabled=settings.outreach_enabled,
        auth_mode=mode,
        auth_local_secret=settings.auth_local_secret,
        oidc_issuer=settings.oidc_issuer,
        oidc_audience=settings.oidc_audience,
        oidc_jwks_url=settings.oidc_jwks_url,
    )


def _validate_runtime(security: RuntimeSecurity, *, jwk_provider: object | None) -> str:
    mode = assert_auth_mode(security.app_env, security.auth_mode)
    if (
        any(origin == "*" for origin in security.allowed_origins)
        or not security.allowed_origins
    ):
        raise RuntimeError("ALLOWED_ORIGINS no puede contener '*' ni quedar vacío")
    if mode == "oidc" and (not security.oidc_issuer or not security.oidc_audience):
        raise RuntimeError(
            "OIDC_ISSUER y OIDC_AUDIENCE son obligatorios en AUTH_MODE=oidc"
        )
    if mode == "oidc" and jwk_provider is None and not security.oidc_jwks_url:
        raise RuntimeError("OIDC_JWKS_URL es obligatorio en AUTH_MODE=oidc")
    return mode


_migrated = False


def prepare_database() -> None:
    """Exige DATABASE_URL y aplica migraciones pendientes una vez por proceso."""
    global _migrated
    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL es obligatoria: el CRM vive en Postgres (schema "
            f"{settings.database_schema}). No hay respaldo SQLite."
        )
    if settings.database_auto_migrate and not _migrated:
        run_migrations(settings.database_url, settings.database_schema)
        _migrated = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.setup_windows_asyncio()
    stop = threading.Event()
    thread = None
    if getattr(app.state, "start_worker", False):
        thread = threading.Thread(
            target=worker_loop,
            args=(app.state.platform, stop),
            name="ashencrm-worker",
            daemon=True,
        )
        thread.start()
    yield
    stop.set()
    if thread is not None:
        thread.join(timeout=2)


def create_app(
    security: RuntimeSecurity | None = None,
    db=None,
    jwk_provider=None,
    platform: PlatformRepository | None = None,
    start_worker: bool = False,
) -> FastAPI:
    active = security or runtime_security_from_settings()
    mode = _validate_runtime(active, jwk_provider=jwk_provider)
    if active.app_env == "production" and not settings.files_bucket:
        raise RuntimeError(
            "FILES_BUCKET es obligatoria en production: el VM no guarda archivos "
            "de negocio en disco (data-platform D2)."
        )
    if db is None or platform is None:
        prepare_database()
    database = db if db is not None else Database()
    provider = jwk_provider
    if provider is None and mode == "oidc":
        provider = HttpJwkProvider(active.oidc_jwks_url)
    authenticator = TokenAuthenticator(
        auth_mode=mode,
        local_secret=active.auth_local_secret,
        oidc_issuer=active.oidc_issuer,
        oidc_audience=active.oidc_audience,
        jwk_provider=provider,
    )

    platform_db = platform or PlatformRepository()
    app = FastAPI(title="Client Acquisition Dashboard", lifespan=lifespan)
    app.state.security = active
    app.state.authenticator = authenticator
    app.state.platform = platform_db
    app.state.start_worker = start_worker
    live = APIRouter()

    @live.get("/api/livez")
    async def livez():
        return {"status": "ok"}

    app.include_router(live)
    app.add_middleware(
        ApiAccessMiddleware,
        authenticator=authenticator,
        audit=platform_db.add_audit,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(active.allowed_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    scrape_service = ScrapeService(database)
    app.include_router(create_auth_router(authenticator))
    app.include_router(create_prospects_router(database))
    app.include_router(create_clients_router(database))
    app.include_router(create_catalog_router(database))
    app.include_router(
        create_admin_router(
            database,
            authenticator,
            sql_console_enabled=active.sql_console_enabled,
        )
    )
    app.include_router(create_scrape_router(scrape_service))
    app.include_router(screenshots_router)
    app.include_router(create_demo_router())
    app.include_router(create_pipeline_router(platform_db))
    app.include_router(create_provider_router(platform_db))

    frontend_dir = ROOT_DIR / "frontend"
    dist_dir = frontend_dir / "dist"
    app.mount(
        "/",
        StaticFiles(
            directory=str(dist_dir if dist_dir.exists() else frontend_dir),
            html=True,
        ),
        name="frontend",
    )
    return app
