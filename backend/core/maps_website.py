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


# Palabras muy genéricas en fichas de Maps; no deben validar un @ por similitud fuzzy.
_IG_GENERIC_NAME_TOKENS = frozenset(
    {
        "dental",
        "dentista",
        "odontologia",
        "odontologos",
        "odontologo",
        "clinica",
        "medellin",
        "bogota",
        "cali",
        "cirugia",
        "estetica",
        "barberia",
        "restaurante",
        "cafeteria",
        "cafe",
        "mejor",
        "oficial",
        "tienda",
        "servicios",
    }
)


def instagram_handle_plausible_for_business(
    handle: str,
    business_name: str,
    website: str = "",
    min_ratio_full: float = 0.43,
    min_ratio_token: float = 0.52,
) -> bool:
    """
    Evita guardar @ de otro negocio (relacionados en Maps, primer link genérico).
    Si hay sitio web, el handle debe alinearse con el dominio o con el nombre.
    """
    if not handle or not str(handle).strip():
        return False
    h = re.sub(r"[^a-z0-9]", "", handle.strip().lstrip("@").lower())
    if len(h) < 2:
        return True

    name_n = _normalize_name(business_name)
    if len(name_n) < 5:
        return True

    if h in name_n or name_n in h:
        return True

    best_full = SequenceMatcher(None, name_n, h).ratio()
    best_token = 0.0
    for raw in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{4,}", business_name):
        t = _normalize_name(raw)
        if len(t) >= 4:
            if t in _IG_GENERIC_NAME_TOKENS:
                continue
            if t in h or h in t:
                return True
            tr = SequenceMatcher(None, t, h).ratio()
            if tr >= min_ratio_token:
                best_token = max(best_token, tr)

    slug = ""
    if website and website.strip():
        try:
            host = (urlparse(website.strip()).netloc or "").lower()
            parts = [
                re.sub(r"[^a-z0-9]", "", p)
                for p in host.split(".")
                if p not in ("www", "com", "co", "org", "net", "site", "app") and len(p) > 2
            ]
            if parts:
                slug = max(parts, key=len)
        except Exception:
            slug = ""

    if slug and len(slug) >= 6:
        r_dom = SequenceMatcher(None, slug, h).ratio()
        if slug in h or h in slug:
            return True
        # Umbral alto: ~0.42 ratio suele ser coincidencia (p. ej. otro negocio del sector)
        if r_dom >= 0.52:
            return True
        # Hay web oficial pero el @ no encaja con el dominio → solo si el nombre respalda
        return best_token >= min_ratio_token or best_full >= min_ratio_full

    if best_token >= min_ratio_token:
        return True
    return best_full >= min_ratio_full
