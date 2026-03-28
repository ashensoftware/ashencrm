"""Pipeline defaults: env solo para credenciales (OPENAI_*, LOVABLE_ACCOUNTS).

Ajustes operativos (ciudad, delays, WhatsApp, mapa, headless de scrape, etc.)
se gestionan en la UI Administración y en `app_settings` (SQLite), con fallback
a los valores por defecto definidos aquí.
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

    def __post_init__(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.browser_data_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
