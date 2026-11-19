"""Dependencias HTTP de autenticación. El dominio del token vive en core.auth."""

from __future__ import annotations

from fastapi import HTTPException, Request

from backend.core.auth import AuthFailure, Principal, TokenAuthenticator


def require_auth(authenticator: TokenAuthenticator):
    def _dependency(request: Request) -> Principal:
        try:
            return authenticator.authenticate(request.headers.get("authorization"))
        except AuthFailure as exc:
            raise HTTPException(
                status_code=exc.status_code, detail=exc.detail
            ) from None

    return _dependency


def require_role(authenticator: TokenAuthenticator, role: str):
    def _dependency(request: Request) -> Principal:
        try:
            principal = authenticator.authenticate(request.headers.get("authorization"))
        except AuthFailure as exc:
            raise HTTPException(
                status_code=exc.status_code, detail=exc.detail
            ) from None
        if principal.role != role:
            raise HTTPException(status_code=403, detail=f"Se requiere rol {role}")
        return principal

    return _dependency
