"""Instagram solo desde el panel del lugar en Maps, no el primer link global."""

import re
from typing import Optional

from backend.core.maps_website import unwrap_google_nav_href

# Misma idea que MAPS_OFFICIAL_WEBSITE_SELECTORS: filas de contacto del negocio,
# no el primer instagram.com del feed (relacionados / otra tarjeta en el panel).
MAPS_OFFICIAL_INSTAGRAM_SELECTORS = [
    'a[aria-label*="Instagram"][href*="instagram.com"]',
    'a[aria-label*="instagram"][href*="instagram.com"]',
    'a[data-item-id*="instagram"][href*="instagram.com"]',
    'a[data-item-id*="social"][href*="instagram.com"]',
]


def _instagram_profile_url_from_href(href: str) -> Optional[str]:
    if not href:
        return None
    raw = unwrap_google_nav_href(href)
    low = raw.lower()
    if "/p/" in low or "/reels/" in low or "/stories/" in low:
        return None
    if "instagram.com" not in low:
        return None
    m = re.search(r"instagram\.com/([^/?#]+)", low)
    if m and m.group(1) in ("p", "reel", "reels", "stories", "explore", "accounts"):
        return None
    return raw.rstrip("/")


async def extract_instagram_from_place_panel(page) -> Optional[str]:
    """
    Restringe búsqueda al panel de detalle del negocio (misma región que el hero).
    Prioriza el enlace explícito tipo «Instagram» del panel; el fallback recorre enlaces
    del panel en orden (sigue siendo mejorable con validación en google_maps).
    """
    try:
        panel = await page.query_selector(
            'div[role="region"]:has(button[jsaction*="pane.heroHeaderImage"])'
        )
        if not panel:
            panel = await page.query_selector('[role="main"]')
        scope = panel or page

        for sel in MAPS_OFFICIAL_INSTAGRAM_SELECTORS:
            try:
                el = await scope.query_selector(sel)
            except Exception:
                el = None
            if not el:
                continue
            try:
                href = await el.get_attribute("href")
            except Exception:
                href = None
            out = _instagram_profile_url_from_href(href or "")
            if out:
                return out

        links = await scope.query_selector_all('a[href*="instagram.com"]')
        for lnk in links:
            try:
                href = await lnk.get_attribute("href")
            except Exception:
                href = None
            out = _instagram_profile_url_from_href(href or "")
            if out:
                return out
    except Exception:
        pass
    return None
