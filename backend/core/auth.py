"""Autenticación por bearer token.

Modo local (development/test): JWT HS256 firmado con AUTH_LOCAL_SECRET.
No hay almacén de contraseñas. El rol sale del claim `role`; los permisos
se derivan en el servidor y no se aceptan desde el token.

Modo oidc: JWT RS256 contra el issuer/audience configurados y un proveedor JWKS.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

import httpx
import jwt

LOCAL_ISSUER = "ashencrm-local"
LOCAL_AUDIENCE = "ashencrm"

ALL_PERMISSIONS = frozenset(
    {
        "records:read",
        "providers:write",
        "campaigns:run",
        "runs:cancel",
        "demos:approve",
        "outreach:approve",
        "outreach:send",
        "admin:settings",
    }
)

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "admin": ALL_PERMISSIONS,
    "operator": frozenset({"records:read", "campaigns:run", "runs:cancel"}),
    "reviewer": frozenset({"records:read", "demos:approve", "outreach:approve"}),
    "viewer": frozenset({"records:read"}),
}

_ROLE_PRECEDENCE = ("admin", "operator", "reviewer", "viewer")


class AuthFailure(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class Principal:
    subject: str
    role: str
    permissions: frozenset[str]
    auth_mode: str


class JwkProvider(Protocol):
    def signing_key(self, token: str) -> Any:
        """Clave pública para verificar un JWT. No debe registrar el token."""


class StaticKeyProvider:
    """Proveedor de pruebas o de una clave ya resuelta. No hace red."""

    def __init__(self, key: Any):
        self._key = key

    def signing_key(self, token: str) -> Any:
        return self._key


class HttpJwkProvider:
    """Descarga JWKS con timeout y un reintento ante fallos transitorios."""

    def __init__(
        self,
        url: str,
        *,
        timeout: float = 5.0,
        client: httpx.Client | None = None,
        backoff_seconds: float = 0.2,
    ):
        if not url:
            raise AuthFailure(503, "OIDC_JWKS_URL es obligatorio en modo oidc")
        self.url = url
        self.backoff_seconds = backoff_seconds
        self._client = client or httpx.Client(timeout=httpx.Timeout(timeout))
        self._jwks: dict[str, Any] | None = None

    def signing_key(self, token: str) -> Any:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError:
            raise AuthFailure(401, "Token inválido") from None
        kid = header.get("kid")
        jwks = self._jwks or self._fetch_jwks()
        self._jwks = jwks
        key = _select_jwk(jwks, kid)
        if key is None:
            self._jwks = self._fetch_jwks()
            key = _select_jwk(self._jwks, kid)
        if key is None:
            raise AuthFailure(401, "Token inválido")
        try:
            return jwt.PyJWK(key).key
        except jwt.InvalidKeyError:
            raise AuthFailure(401, "Token inválido") from None

    def _fetch_jwks(self) -> dict[str, Any]:
        last_status: int | None = None
        for attempt in range(2):
            try:
                response = self._client.get(self.url)
            except httpx.TimeoutException:
                if attempt == 0:
                    time.sleep(self.backoff_seconds)
                    continue
                raise AuthFailure(
                    503, "Tiempo de espera agotado al consultar JWKS"
                ) from None
            except httpx.HTTPError:
                raise AuthFailure(503, "No se pudo consultar JWKS") from None
            last_status = response.status_code
            if response.status_code in {429, 500, 502, 503, 504} and attempt == 0:
                time.sleep(self.backoff_seconds)
                continue
            if response.status_code != 200:
                raise AuthFailure(
                    503, "El proveedor OIDC rechazó la consulta de claves"
                )
            try:
                payload = response.json()
            except ValueError:
                raise AuthFailure(503, "JWKS inválido") from None
            if not isinstance(payload, dict):
                raise AuthFailure(503, "JWKS inválido")
            return payload
        if last_status == 429:
            raise AuthFailure(
                503, "El proveedor de identidad limitó la consulta de claves"
            )
        raise AuthFailure(503, "No se pudo consultar JWKS")


def issue_local_token(
    secret: str,
    role: str,
    subject: str = "local-user",
    ttl_seconds: int = 8 * 3600,
) -> str:
    if role not in ROLE_PERMISSIONS:
        raise ValueError("Rol no reconocido")
    if not secret:
        raise ValueError("AUTH_LOCAL_SECRET vacío")
    now = int(time.time())
    payload = {
        "sub": subject,
        "role": role,
        "iss": LOCAL_ISSUER,
        "aud": LOCAL_AUDIENCE,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    encoded = jwt.encode(payload, secret, algorithm="HS256")
    if isinstance(encoded, bytes):
        return encoded.decode("ascii")
    return encoded


def principal_from_claims(claims: Mapping[str, Any], *, auth_mode: str) -> Principal:
    role = _role_from_claims(claims)
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise AuthFailure(401, "Token inválido")
    return Principal(
        subject=subject,
        role=role,
        permissions=ROLE_PERMISSIONS[role],
        auth_mode=auth_mode,
    )


def _role_from_claims(claims: Mapping[str, Any]) -> str:
    found: set[str] = set()
    role = claims.get("role")
    if isinstance(role, str):
        found.add(role)
    roles = claims.get("roles")
    if isinstance(roles, str):
        found.add(roles)
    elif isinstance(roles, list):
        found.update(item for item in roles if isinstance(item, str))
    known = found.intersection(ROLE_PERMISSIONS)
    for candidate in _ROLE_PRECEDENCE:
        if candidate in known:
            return candidate
    raise AuthFailure(403, "El token no incluye un rol reconocido")


class TokenAuthenticator:
    def __init__(
        self,
        *,
        auth_mode: str,
        local_secret: str = "",
        oidc_issuer: str = "",
        oidc_audience: str = "",
        jwk_provider: JwkProvider | None = None,
    ):
        self.auth_mode = auth_mode
        self.local_secret = local_secret
        self.oidc_issuer = oidc_issuer
        self.oidc_audience = oidc_audience
        self.jwk_provider = jwk_provider

    def authenticate(self, authorization: str | None) -> Principal:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise AuthFailure(401, "Se requiere Authorization: Bearer")
        token = authorization.split(" ", 1)[1].strip()
        if not token:
            raise AuthFailure(401, "Se requiere Authorization: Bearer")
        try:
            if self.auth_mode == "local":
                return self._authenticate_local(token)
            if self.auth_mode == "oidc":
                return self._authenticate_oidc(token)
        except AuthFailure:
            raise
        except jwt.ExpiredSignatureError:
            raise AuthFailure(401, "Token expirado") from None
        except jwt.InvalidTokenError:
            raise AuthFailure(401, "Token inválido") from None
        raise AuthFailure(401, "Modo de autenticación no configurado")

    def _authenticate_local(self, token: str) -> Principal:
        if not self.local_secret:
            raise AuthFailure(401, "AUTH_LOCAL_SECRET no está configurado")
        payload = jwt.decode(
            token,
            self.local_secret,
            algorithms=["HS256"],
            audience=LOCAL_AUDIENCE,
            issuer=LOCAL_ISSUER,
            options={"require": ["exp", "iat", "sub", "role"]},
        )
        return principal_from_claims(payload, auth_mode="local")

    def _authenticate_oidc(self, token: str) -> Principal:
        if not self.oidc_issuer or not self.oidc_audience:
            raise AuthFailure(503, "OIDC_ISSUER y OIDC_AUDIENCE son obligatorios")
        if self.jwk_provider is None:
            raise AuthFailure(503, "Proveedor OIDC sin JWKS configurado")
        key = self.jwk_provider.signing_key(token)
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=self.oidc_audience,
            issuer=self.oidc_issuer,
            options={"require": ["exp", "sub"]},
        )
        return principal_from_claims(payload, auth_mode="oidc")


def _select_jwk(jwks: Mapping[str, Any], kid: str | None) -> dict[str, Any] | None:
    keys = jwks.get("keys")
    if not isinstance(keys, list):
        return None
    dict_keys = [item for item in keys if isinstance(item, dict)]
    if kid:
        for item in dict_keys:
            if item.get("kid") == kid:
                return item
        return None
    if len(dict_keys) == 1:
        return dict_keys[0]
    return None


if __name__ == "__main__":
    import os

    secret = os.getenv("AUTH_LOCAL_SECRET", "")
    if not secret:
        raise SystemExit("AUTH_LOCAL_SECRET no está definido")
    role = sys.argv[1] if len(sys.argv) > 1 else "admin"
    sys.stdout.write(issue_local_token(secret, role))
    sys.stdout.write("\n")
