"""Identidad de negocio: no basta el nombre."""

from __future__ import annotations

import re
from urllib.parse import urlparse

try:
    import phonenumbers
except ImportError:  # pragma: no cover
    phonenumbers = None

_DOMAIN = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")


def canonical_domain(value: str | None) -> str | None:
    if not value or not isinstance(value, str):
        return None
    raw = value.strip().lower()
    if not raw:
        return None
    if "://" not in raw:
        raw = "https://" + raw
    host = (urlparse(raw).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if not _DOMAIN.match(host):
        return None
    return host


def phone_e164(value: str | None, region: str = "CO") -> str | None:
    if not value or not isinstance(value, str):
        return None
    if phonenumbers is None:
        digits = "".join(ch for ch in value if ch.isdigit())
        if digits.startswith("57") and len(digits) == 12:
            return "+" + digits
        if len(digits) == 10:
            return "+57" + digits
        return None
    try:
        parsed = phonenumbers.parse(value, region)
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_possible_number(parsed):
        return None
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def email_syntax_ok(value: str | None) -> bool:
    if not value or not isinstance(value, str):
        return False
    text = value.strip().lower()
    if text.count("@") != 1:
        return False
    local, domain = text.split("@")
    return bool(local) and canonical_domain(domain) is not None and " " not in text


def identity_keys(*, provider: str, external_id: str | None, domain: str | None, phone: str | None) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    if external_id:
        keys.append((f"provider:{provider}", external_id.strip()))
    if domain:
        keys.append(("domain", domain))
    if phone:
        keys.append(("phone", phone))
    return keys
