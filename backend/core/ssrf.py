"""Destinos que el servidor no debe solicitar (SSRF)."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


def _blocked_ip(raw: str) -> bool:
    try:
        ip = ipaddress.ip_address(raw)
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def is_safe_public_url(url: str | None) -> bool:
    if not url or not isinstance(url, str):
        return False
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False
    host = parsed.hostname.strip("[]").lower()
    if host in {"localhost", "metadata.google.internal"} or host.endswith(".local"):
        return False
    if _blocked_ip(host):
        return False
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror:
        return False
    addresses = [item[4][0] for item in infos]
    if not addresses or any(_blocked_ip(addr) for addr in addresses):
        return False
    return True
