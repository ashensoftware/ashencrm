"""Extrae la URL del sitio web solo desde acciones oficiales del panel de Maps."""

import re
from typing import Optional

from backend.core.maps_website import (
    MAPS_OFFICIAL_WEBSITE_SELECTORS,
    unwrap_google_nav_href,
)


async def extract_official_website_from_maps_page(page) -> Optional[str]:
    """
    Solo el botón/acción "Sitio web" del lugar. Evita el primer `a[href^=http]` de la página
    (relacionados, reservas de terceros, etc.).
    """
    for sel in MAPS_OFFICIAL_WEBSITE_SELECTORS:
        try:
            links = await page.query_selector_all(sel)
        except Exception:
            continue
        for link in links:
            try:
                href = await link.get_attribute("href")
            except Exception:
                href = None
            if not href:
                continue
            raw = unwrap_google_nav_href(href)
            low = raw.lower()
            if "instagram.com" in low or "facebook.com" in low:
                continue
            if "maps.google.com" in low or "google.com/maps" in low:
                continue
            if "googleusercontent.com" in low:
                continue
            if "duckduckgo.com" in low:
                continue
            if "google.com" in low or "gstatic.com" in low:
                continue
            if re.search(r"\.[a-z]{2,}(/|$)", low):
                return raw.rstrip(".")
    return None
