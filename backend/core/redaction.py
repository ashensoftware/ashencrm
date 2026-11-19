"""Redacción central de secretos antes de logs, eventos o respuestas de diagnóstico."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

REDACTED = "[REDACTED]"

_SENSITIVE_KEY = re.compile(
    r"(?i)(?:^|[_\-])("
    r"password|passwd|secret|api[_-]?key|refresh[_-]?token|access[_-]?token|"
    r"id[_-]?token|client[_-]?secret|authorization|cookie|set-cookie|"
    r"x-api-key|x-api-token|proxy-authorization"
    r")(?:$|[_\-])"
)

_BEARER = re.compile(r"(?i)\bBearer\s+\S+")
_ASSIGNMENT = re.compile(
    r"(?i)\b("
    r"authorization|cookie|set-cookie|x-api-key|x-api-token|proxy-authorization|"
    r"password|passwd|secret|api[_-]?key|refresh[_-]?token|access[_-]?token|"
    r"id[_-]?token|client[_-]?secret"
    r")\b(\s*[:=]\s*)(\S+)"
)
_JSON_SECRET = re.compile(
    r'(?i)("(?:password|passwd|secret|api_key|apiKey|api-key|refresh_token|'
    r"refreshToken|access_token|accessToken|id_token|idToken|client_secret|"
    r'clientSecret|authorization|cookie|set-cookie|x-api-key)"\s*:\s*")([^"]*)(")'
)


def is_sensitive_key(key: str) -> bool:
    return _SENSITIVE_KEY.search(str(key)) is not None


def redact_text(text: str) -> str:
    if not text:
        return text
    redacted = _BEARER.sub(f"Bearer {REDACTED}", text)
    redacted = _JSON_SECRET.sub(rf"\1{REDACTED}\3", redacted)
    redacted = _ASSIGNMENT.sub(rf"\1\2{REDACTED}", redacted)
    return redacted


def redact_headers(headers: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in headers.items():
        name = str(key)
        if is_sensitive_key(name):
            redacted[name] = REDACTED
        elif isinstance(value, str):
            redacted[name] = redact_text(value)
        else:
            redacted[name] = value
    return redacted


def redact_data(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): (REDACTED if is_sensitive_key(str(key)) else redact_data(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_data(item) for item in value)
    if isinstance(value, str):
        return redact_text(value)
    return value
