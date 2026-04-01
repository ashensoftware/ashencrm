"""Helpers for extracting and validating business websites from Google Maps."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse

# Solo enlaces del panel de lugar que corresponden al botón "Sitio web" / Website.
# No usar `a[href^="http"]`: captura el primer link arbitrario (ads, "relacionados", agregadores).
MAPS_OFFICIAL_WEBSITE_SELECTORS = [
    'a[data-item-id="authority"]',
    'a[data-item-id*="authority"]',
    'a[aria-label*="Sitio web"]',
    'a[aria-label*="sitio web"]',
    'a[aria-label*="Website"]',
    'a[aria-label*="website"]',
]


def unwrap_google_nav_href(href: str) -> str:
    """
    Devuelve la URL destino si Google envuelve el enlace (url?q=...).
    """
    if not href:
        return href
    h = href.strip()
    low = h.lower()
    if "google.com/url" in low or "/url?" in low:
        try:
            parsed = urlparse(h)
            qs = parse_qs(parsed.query)
            if "q" in qs and qs["q"]:
                return unquote(qs["q"][0]).strip()
            if "url" in qs and qs["url"]:
                return unquote(qs["url"][0]).strip()
        except Exception:
            pass
    return h


def _normalize_name(name: str) -> str:
    if not name:
        return ""
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", n)


def website_plausible_for_business(url: str, business_name: str, min_ratio: float = 0.42) -> bool:
    """
    Evita asignar webs de otro negocio (p. ej. subdominio agendapro de "Barberia Rand"
    a un lead "Go Barber Shop"). No es perfecto pero corta muchos falsos positivos
    de búsqueda web / primer link genérico.
    """
    if not url or not url.strip():
        return False
    name = _normalize_name(business_name)
    if len(name) < 5:
        return True

    try:
        parsed = urlparse(url.strip())
        host = (parsed.netloc or "").lower()
    except Exception:
        return False
    if not host:
        return False

    # Etiquetas del host (sin TLDs genéricos)
    skip_labels = {
        "www",
        "com",
        "co",
        "net",
        "org",
        "site",
        "app",
        "html",
        "https",
        "http",
    }
    parts = [p for p in host.split(".") if p and p not in skip_labels]

    # Multi-tenant: el slug del negocio suele ir en el primer subdominio (p. ej. barberiarand.site.agendapro.com)
    if "agendapro" in host or "booksy" in host or "fresha" in host:
        slug = parts[0] if parts else ""
        if slug and slug not in ("agendapro", "booksy", "fresha", "www"):
            r = SequenceMatcher(None, name, slug).ratio()
            if r < max(min_ratio + 0.08, 0.52):
                return False

    joined = "".join(parts)
    if len(joined) < 4:
        return True

    best = SequenceMatcher(None, name, joined).ratio()
    for p in parts:
        if len(p) >= 4:
            best = max(best, SequenceMatcher(None, name, p).ratio())

    return best >= min_ratio
