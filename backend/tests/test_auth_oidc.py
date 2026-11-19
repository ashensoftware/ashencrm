"""OIDC RS256 y redacción de claims de permisos no confiables."""

import json
import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from backend.core.auth import (
    ALL_PERMISSIONS,
    HttpJwkProvider,
    StaticKeyProvider,
    TokenAuthenticator,
    issue_local_token,
)


def _rsa_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def _jwks(public_key, kid="k1") -> dict:
    data = json.loads(RSAAlgorithm.to_jwk(public_key))
    data.update({"kid": kid, "use": "sig", "alg": "RS256"})
    return {"keys": [data]}


def test_oidc_token_uses_role_not_client_supplied_permissions():
    private_key, public_key = _rsa_pair()
    token = jwt.encode(
        {
            "sub": "oidc-user",
            "role": "viewer",
            "permissions": sorted(ALL_PERMISSIONS),
            "iss": "https://issuer.example",
            "aud": "ashencrm",
            "exp": int(time.time()) + 600,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "k1"},
    )
    authenticator = TokenAuthenticator(
        auth_mode="oidc",
        oidc_issuer="https://issuer.example",
        oidc_audience="ashencrm",
        jwk_provider=StaticKeyProvider(public_key),
    )
    principal = authenticator.authenticate(f"Bearer {token}")
    assert principal.role == "viewer"
    assert principal.permissions == frozenset({"records:read"})
    assert "admin:settings" not in principal.permissions


def test_jwks_client_retries_transient_failure_then_validates():
    private_key, public_key = _rsa_pair()
    document = _jwks(public_key)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, json={"error": "unavailable"})
        return httpx.Response(200, json=document)

    provider = HttpJwkProvider(
        "https://issuer.example/jwks",
        client=httpx.Client(transport=httpx.MockTransport(handler), timeout=5.0),
        backoff_seconds=0,
    )
    token = jwt.encode(
        {
            "sub": "oidc-admin",
            "role": "admin",
            "iss": "https://issuer.example",
            "aud": "ashencrm",
            "exp": int(time.time()) + 600,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "k1"},
    )
    authenticator = TokenAuthenticator(
        auth_mode="oidc",
        oidc_issuer="https://issuer.example",
        oidc_audience="ashencrm",
        jwk_provider=provider,
    )
    principal = authenticator.authenticate(f"Bearer {token}")
    assert principal.role == "admin"
    assert "outreach:send" in principal.permissions
    assert calls["n"] == 2
    assert token not in json.dumps(document)


def test_local_token_rejects_wrong_secret():
    token = issue_local_token("one-secret", "admin")
    authenticator = TokenAuthenticator(auth_mode="local", local_secret="other-secret")
    from backend.core.auth import AuthFailure

    with pytest.raises(AuthFailure) as caught:
        authenticator.authenticate(f"Bearer {token}")
    assert caught.value.status_code == 401
    assert token not in caught.value.detail
