"""Acceso a la base para los scripts locales (scraper, enriquecimiento, limpieza).

Usan el rol `crm_ingest` (DATABASE_INGEST_URL): SELECT/INSERT/UPDATE solo en
`prospects` y `category_catalog`, sin DELETE, sin clientes, ajustes ni la cola.
Nunca caen a DATABASE_URL (`crm_app`): un script del PC no debe poder tocar más
que eso aunque tenga un bug. Lo que necesite más va detrás de la API.
"""

from __future__ import annotations

import atexit
from urllib.parse import unquote, urlsplit

from backend.infrastructure.persistence.pg import make_pool
from backend.infrastructure.persistence.prospect_repository import ProspectRepository

INGEST_ROLE = "crm_ingest"


def ingest_role(url: str) -> str:
    """Rol de la URL. El pooler de Supabase usa `<rol>.<ref-del-proyecto>`."""
    user = unquote(urlsplit(url).username or "")
    return user.split(".", 1)[0]


def ingest_repository() -> ProspectRepository:
    from backend.config.settings import settings

    url = settings.database_ingest_url
    if not url:
        raise RuntimeError(
            "DATABASE_INGEST_URL no está configurada (rol crm_ingest). "
            "Los scripts locales no usan DATABASE_URL. Ver .env.example."
        )
    role = ingest_role(url)
    if role != INGEST_ROLE:
        raise RuntimeError(
            f"DATABASE_INGEST_URL usa el rol {role or '?'!r}; debe ser {INGEST_ROLE}."
        )
    pool = make_pool(url, settings.database_schema, min_size=1, max_size=2, name="ashencrm-ingest")
    atexit.register(pool.close)
    return ProspectRepository(pool=pool)
