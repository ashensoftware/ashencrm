from fastapi import APIRouter, Depends

from backend.api.dependencies import require_auth
from backend.core.auth import Principal, TokenAuthenticator


def create_auth_router(authenticator: TokenAuthenticator) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["Auth"])
    require_user = require_auth(authenticator)

    @router.get("/config")
    async def auth_config():
        return {
            "auth_mode": authenticator.auth_mode,
            "token_storage": "sessionStorage",
            "production_requires_oidc": True,
        }

    @router.get("/me")
    async def me(principal: Principal = Depends(require_user)):
        return {
            "subject": principal.subject,
            "role": principal.role,
            "permissions": sorted(principal.permissions),
            "auth_mode": principal.auth_mode,
        }

    return router
