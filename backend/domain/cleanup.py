"""Limpieza de datos de scraping. Funciones puras e idempotentes.

Las usan la importación única desde SQLite y el repositorio en cada inserción y
búsqueda por (name, address), para que un lead re-scrapeado con la dirección
"sucia" siga deduplicándose contra la versión limpia.
"""

from __future__ import annotations

import re

# Por encima de esto el scraper leyó otro número (p. ej. seguidores). NULL = desconocido.
REVIEWS_COUNT_MAX = 50_000

_STATUS_SUFFIX_RE = re.compile(
    r"\s*(Abierto( las 24 horas)?|Cierra pronto|Abre pronto|Cerrado( temporalmente| permanentemente)?)$"
)
_PLACE_ID_RE = re.compile(r"!19s(ChIJ[\w-]+)")
_SPACES_RE = re.compile(r"[\s    ]+")


def _is_private_use(ch: str) -> bool:
    cp = ord(ch)
    return 0xE000 <= cp <= 0xF8FF or 0xF0000 <= cp <= 0x10FFFD


def clean_address(raw: str | None) -> str:
    """`Barbería · \\ue934 · Cra. 76 #26-20` -> `Cra. 76 #26-20`.

    El scraper guardó el texto de la tarjeta de Maps separado por " · ":
    `categoría · [ícono] · dirección[estado] · horario · teléfono...`.
    Quita los íconos (área de uso privado), y si hay varias partes se queda con
    la segunda (la dirección) y le quita el estado pegado al final ("Abierto").
    El resultado nunca contiene "·", así que aplicarla dos veces no cambia nada.
    """
    if not raw:
        return ""
    text = "".join(ch for ch in raw if not _is_private_use(ch))
    text = _SPACES_RE.sub(" ", text)
    parts = [p.strip() for p in text.split("·") if p.strip()]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return _STATUS_SUFFIX_RE.sub("", parts[1]).strip()


def extract_google_place_id(maps_url: str | None) -> str | None:
    match = _PLACE_ID_RE.search(maps_url or "")
    return match.group(1) if match else None


def split_legacy_photo(screenshot_path: str | None) -> tuple[str, str | None]:
    """El scraper guardaba la foto de Maps (URL firmada) en screenshot_path, que es
    para la captura de la demo. Devuelve (screenshot_path, legacy_photo_url)."""
    value = (screenshot_path or "").strip()
    if value.lower().startswith(("http://", "https://")):
        return "", value
    return value, None


def plausible_reviews_count(value: int | None) -> int | None:
    if value is None:
        return None
    try:
        count = int(value)
    except (TypeError, ValueError):
        return None
    if count < 0 or count > REVIEWS_COUNT_MAX:
        return None
    return count
