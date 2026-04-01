"""Instagram solo desde el panel del lugar en Maps, no el primer link global."""

import re
from typing import Optional

from backend.core.maps_website import unwrap_google_nav_href


async def extract_instagram_from_place_panel(page) -> Optional[str]:
    """
    Restringe búsqueda al panel de detalle del negocio (misma región que el hero).
    Evita el primer instagram.com de la página (relacionados, competencia, anuncios).
    """
    try:
        panel = await page.query_selector(
            'div[role="region"]:has(button[jsaction*="pane.heroHeaderImage"])'
        )
        if not panel:
            panel = await page.query_selector('[role="main"]')
        scope = panel or page
        links = await scope.query_selector_all('a[href*="instagram.com"]')
        for lnk in links:
            try:
                href = await lnk.get_attribute("href")
            except Exception:
                href = None
            if not href:
                continue
            raw = unwrap_google_nav_href(href)
            low = raw.lower()
            if "/p/" in low or "/reels/" in low or "/stories/" in low:
                continue
            if "instagram.com" not in low:
                continue
            m = re.search(r"instagram\.com/([^/?#]+)", low)
            if m and m.group(1) in ("p", "reel", "reels", "stories", "explore", "accounts"):
                continue
            return raw.rstrip("/")
    except Exception:
        pass
    return None
