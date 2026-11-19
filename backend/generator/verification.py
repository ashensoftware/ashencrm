"""Verificación mínima de artefactos de demo.

Una URL con valor, o el placeholder histórico `demo-account_N.lovable.app`,
no es un éxito. DEMO_CREATED exige URL de Lovable aceptable y un archivo
de captura existente y no vacío. La verificación de deployment queda para
una iteración posterior.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

_PLACEHOLDER_HOST = re.compile(r"(?i)^demo-account[_-]?\d+\.lovable\.app$")
_LOVABLE_APP_HOSTS = {"lovable.app", "www.lovable.app"}
_LOVABLE_DEV_HOSTS = {"lovable.dev", "www.lovable.dev"}


def is_placeholder_demo_url(url: str | None) -> bool:
    if not url or not isinstance(url, str):
        return False
    host = (urlparse(url.strip()).hostname or "").lower()
    return _PLACEHOLDER_HOST.match(host) is not None


def is_acceptable_demo_url(url: str | None) -> bool:
    if not url or not isinstance(url, str):
        return False
    raw = url.strip()
    if not raw or is_placeholder_demo_url(raw):
        return False
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host.endswith(".lovable.app") and host not in _LOVABLE_APP_HOSTS:
        return True
    if host in _LOVABLE_DEV_HOSTS and "/projects/" in parsed.path:
        return True
    return False


def screenshot_file_verified(path: str | None) -> bool:
    if not path or not isinstance(path, str):
        return False
    try:
        file_path = Path(path)
        return file_path.is_file() and file_path.stat().st_size > 0
    except OSError:
        return False


def conclude_lovable_preview(found_url: str | None, *, timed_out: bool) -> str | None:
    """Cierra la búsqueda de preview. Un timeout nunca fabrica una URL."""
    if timed_out or not is_acceptable_demo_url(found_url):
        return None
    assert found_url is not None
    return found_url.strip().split("?", 1)[0]
