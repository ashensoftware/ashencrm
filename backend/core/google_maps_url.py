"""Extrae coordenadas y nombre de sitio desde enlaces de Google Maps."""

from __future__ import annotations

import re
from urllib.parse import unquote, urlparse, parse_qs
from urllib.request import Request, urlopen


def extract_place_name(url: str) -> str | None:
    m = re.search(r"/place/([^/@?#]+)/", url)
    if not m:
        return None
    raw = m.group(1)
    name = unquote(raw.replace("+", " ")).strip()
    return name or None


def extract_lat_lng_from_text(text: str) -> tuple[float, float] | None:
    """Busca lat/lng en distintos formatos usados por Google Maps."""
    chunks = [text]
    if "#" in text:
        chunks.extend(text.split("#"))

    for chunk in chunks:
        # Formato !3d(lat)!4d(lng) en data= o fragmentos
        m = re.search(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)", chunk)
        if m:
            return float(m.group(1)), float(m.group(2))

        # @lat,lng con zoom opcional (17z, 17.5z, etc.)
        m = re.search(
            r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)(?:,\d+(?:\.\d+)?z|\?|/|$|,)",
            chunk,
        )
        if m:
            return float(m.group(1)), float(m.group(2))

        # @lat,lng fin de segmento (respaldo si el patrón con zoom no coincide)
        m = re.search(r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)(?:/|$)", chunk)
        if m:  # pragma: no cover
            return float(m.group(1)), float(m.group(2))

    parsed = urlparse(text)
    qs = parse_qs(parsed.query)

    for key in ("q", "query", "center"):
        if key not in qs:
            continue
        part = unquote(qs[key][0]).strip()
        m = re.match(r"^(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)$", part)
        if m:
            return float(m.group(1)), float(m.group(2))

    if "ll" in qs:
        part = qs["ll"][0].strip()
        m = re.match(r"^(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)$", part)
        if m:
            return float(m.group(1)), float(m.group(2))

    return None


def resolve_short_url(url: str, timeout: float = 25.0) -> str:
    """Sigue redirecciones (p. ej. maps.app.goo.gl) y devuelve la URL final."""
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; AshenCRM/1.0; +https://example.local)"
        },
        method="GET",
    )
    with urlopen(req, timeout=timeout) as resp:
        return resp.geturl()


def parse_google_maps_link(url: str) -> dict:
    """
    Devuelve latitude, longitude, resolved_url, suggested_display_name.
    Lanza ValueError si no hay coordenadas o la URL es inválida.
    """
    raw = (url or "").strip()
    if not raw:
        raise ValueError("Pega un enlace de Google Maps")

    if "://" not in raw:
        raw = "https://" + raw

    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("La URL debe ser http o https")

    host = (parsed.netloc or "").lower()
    if "google" not in host and "goo.gl" not in host and "maps.app" not in host:
        raise ValueError("El enlace no parece ser de Google Maps")

    coords = extract_lat_lng_from_text(raw)
    resolved = raw
    suggested = extract_place_name(raw) or ""

    if coords is None:
        try:
            resolved = resolve_short_url(raw)
        except Exception as e:
            raise ValueError(
                "No se pudo abrir el enlace. Copia el enlace completo desde "
                f"Google Maps (Compartir). ({e})"
            ) from e
        coords = extract_lat_lng_from_text(resolved)
        if not suggested:
            suggested = extract_place_name(resolved) or ""

    if coords is None:
        raise ValueError(
            "No se encontraron coordenadas en el enlace. Abre el lugar en Google Maps, "
            "pulsa Compartir y copia el enlace completo."
        )

    lat, lng = coords
    return {
        "latitude": lat,
        "longitude": lng,
        "resolved_url": resolved,
        "suggested_display_name": suggested,
    }
