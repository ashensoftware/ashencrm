"""Pipeline defaults: env solo para credenciales (OPENAI_*, LOVABLE_ACCOUNTS).

Ajustes operativos (ciudad, delays, WhatsApp, mapa, headless de scrape, etc.)
se gestionan en la UI Administración y en `crm.app_settings` (Postgres), con
fallback a los valores por defecto definidos aquí.
"""

import asyncio
import json
import os
import platform
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

if platform.system() == "Windows":
    try:
        if not isinstance(
            asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy
        ):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass
class ScraperConfig:
    city: str = os.getenv("DEFAULT_CITY", "Medellín")
    categories: list[str] = field(
        default_factory=lambda: os.getenv(
            "DEFAULT_CATEGORIES", "gym,restaurante,barbería,spa"
        ).split(",")
    )
    ig_min_delay: float = float(os.getenv("IG_MIN_DELAY", "3"))
    ig_max_delay: float = float(os.getenv("IG_MAX_DELAY", "8"))
    max_results_per_category: int = int(os.getenv("MAX_RESULTS_PER_CATEGORY", "100"))
    headless: bool = os.getenv("HEADLESS", "true").lower() == "true"


@dataclass
class GeneratorConfig:
    openai_email: str = os.getenv("OPENAI_EMAIL", "")
    openai_password: str = os.getenv("OPENAI_PASSWORD", "")
    lovable_timeout: int = int(os.getenv("LOVABLE_TIMEOUT", "180"))
    lovable_headless: bool = os.getenv("LOVABLE_HEADLESS", "true").lower() == "true"

    def load_lovable_accounts(self) -> list[dict]:
        raw = os.getenv("LOVABLE_ACCOUNTS", "[]")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return []


@dataclass
class OutreachConfig:
    whatsapp_phone: str = os.getenv("WHATSAPP_PHONE", "3105602568")
    whatsapp_min_delay: int = int(os.getenv("WHATSAPP_MIN_DELAY", "30"))
    whatsapp_max_delay: int = int(os.getenv("WHATSAPP_MAX_DELAY", "120"))
    whatsapp_max_daily: int = int(os.getenv("WHATSAPP_MAX_DAILY", "25"))


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    scraper: ScraperConfig = field(default_factory=ScraperConfig)
    generator: GeneratorConfig = field(default_factory=GeneratorConfig)
    outreach: OutreachConfig = field(default_factory=OutreachConfig)
    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / "data"
    screenshots_dir: Path = PROJECT_ROOT / "data" / "screenshots"
    browser_data_dir: Path = PROJECT_ROOT / "data" / "browser_data"
    db_path: Path = PROJECT_ROOT / "data" / "db" / "prospects.db"
    sessions_dir: Path = PROJECT_ROOT / "data" / "sessions"
    exports_dir: Path = PROJECT_ROOT / "data" / "exports"
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    allowed_origins_raw: str = field(default_factory=lambda: os.getenv("ALLOWED_ORIGINS", ""))
    allowed_origins: list[str] = field(default_factory=list)
    outreach_enabled: bool = field(default_factory=lambda: _env_bool("OUTREACH_ENABLED", False))
    auth_mode: str = field(
        default_factory=lambda: (os.getenv("AUTH_MODE", "local") or "local").strip().lower()
    )
    auth_local_secret: str = field(default_factory=lambda: os.getenv("AUTH_LOCAL_SECRET", ""))
    oidc_issuer: str = field(default_factory=lambda: (os.getenv("OIDC_ISSUER", "") or "").strip())
    oidc_audience: str = field(
        default_factory=lambda: (os.getenv("OIDC_AUDIENCE", "") or "").strip()
    )
    oidc_jwks_url: str = field(
        default_factory=lambda: (os.getenv("OIDC_JWKS_URL", "") or "").strip()
    )
    sql_console_production_ack: str = field(
        default_factory=lambda: os.getenv("SQL_CONSOLE_PRODUCTION_ACK", "")
    )
    # Apagada salvo ALLOW_SQL_CONSOLE=1. En production además hace falta el acuse.
    sql_console_enabled: bool = False
    security_error: str | None = None
    legacy_maps_scraper_enabled: bool = field(
        default_factory=lambda: _env_bool("LEGACY_MAPS_SCRAPER_ENABLED", False)
    )
    lovable_browser_automation_enabled: bool = field(
        default_factory=lambda: _env_bool("LOVABLE_BROWSER_AUTOMATION_ENABLED", False)
    )
    discovery_provider: str = field(
        default_factory=lambda: os.getenv("DISCOVERY_PROVIDER", "simulated").strip().lower()
        or "simulated"
    )
    platform_secret_key: str = field(default_factory=lambda: os.getenv("PLATFORM_SECRET_KEY", ""))
    google_places_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_PLACES_API_KEY", ""))
    # Solo origen de la importación única a Postgres (D4); la app ya no los abre.
    platform_db_path: Path = PROJECT_ROOT / "data" / "db" / "platform.db"
    # Postgres (Supabase, pooler en modo sesión). DATABASE_URL usa el rol crm_app;
    # DATABASE_READONLY_URL el rol crm_readonly (consola SQL).
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "").strip())
    database_readonly_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_READONLY_URL", "").strip()
    )
    database_schema: str = field(
        default_factory=lambda: os.getenv("DATABASE_SCHEMA", "crm").strip() or "crm"
    )
    database_auto_migrate: bool = field(
        default_factory=lambda: _env_bool("DATABASE_AUTO_MIGRATE", True)
    )
    supabase_url: str = field(
        default_factory=lambda: os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    )
    supabase_publishable_key: str = field(
        default_factory=lambda: os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
    )
    supabase_secret_key: str = field(
        default_factory=lambda: os.getenv("SUPABASE_SECRET_KEY", "").strip()
    )
    supabase_jwks_url: str = field(
        default_factory=lambda: os.getenv("SUPABASE_JWKS_URL", "").strip()
    )

    def __post_init__(self) -> None:
        from backend.core.security_policy import (
            resolve_allowed_origins,
            resolve_sql_console_enabled,
        )

        self.sql_console_enabled = resolve_sql_console_enabled(
            self.app_env,
            os.getenv("ALLOW_SQL_CONSOLE"),
            self.sql_console_production_ack,
        )
        try:
            self.allowed_origins = resolve_allowed_origins(
                self.app_env, self.allowed_origins_raw
            )
            self.security_error = None
        except RuntimeError as exc:
            self.allowed_origins = []
            self.security_error = str(exc)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.browser_data_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if self.supabase_url:
            if not self.oidc_issuer:
                self.oidc_issuer = f"{self.supabase_url}/auth/v1"
            if not self.oidc_jwks_url:
                self.oidc_jwks_url = self.supabase_jwks_url or (
                    f"{self.supabase_url}/auth/v1/.well-known/jwks.json"
                )
            if not self.oidc_audience:
                self.oidc_audience = "authenticated"
            explicit_mode = os.getenv("AUTH_MODE", "").strip().lower()
            if explicit_mode in {"", "local"} and self.supabase_jwks_url:
                self.auth_mode = "oidc"


settings = Settings()
