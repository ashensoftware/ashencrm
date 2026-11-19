"""Conexiones de Lovable. Solo OAuth/MCP. El token no vuelve al cliente."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.config.settings import settings
from backend.core.secrets import encrypt_secret, secret_last4
from backend.infrastructure.persistence.platform_repository import PlatformRepository
from backend.infrastructure.providers.lovable_mcp import LovableMcpClient, documented_capabilities


def create_provider_router(platform: PlatformRepository) -> APIRouter:
    router = APIRouter(prefix="/api/admin/providers/lovable", tags=["Providers"])

    @router.get("/capabilities")
    async def capabilities():
        return documented_capabilities()

    @router.get("")
    async def list_connections():
        return {"connections": platform.list_connections()}

    @router.post("")
    async def create_connection(body: dict):
        label = str(body.get("label") or "").strip()
        if not label:
            raise HTTPException(status_code=400, detail="label es obligatorio")
        token = body.get("access_token")
        ciphertext = None
        last4 = None
        if isinstance(token, str) and token.strip():
            if not settings.platform_secret_key:
                raise HTTPException(
                    status_code=409,
                    detail="PLATFORM_SECRET_KEY es obligatoria para guardar un token",
                )
            ciphertext = encrypt_secret(token.strip(), settings.platform_secret_key)
            last4 = secret_last4(token)
        connection_id = platform.add_connection(
            label=label,
            ciphertext=ciphertext,
            last4=last4,
            workspace=body.get("workspace") if isinstance(body.get("workspace"), str) else None,
        )
        return {
            "id": connection_id,
            "auth_method": "oauth",
            "secret_last4": last4,
            "status": "ready" if ciphertext else "needs_authorization",
        }

    @router.post("/{connection_id}/check")
    async def check_connection(connection_id: str):
        rows = platform.list_connections()
        found = next((row for row in rows if row["id"] == connection_id), None)
        if not found:
            raise HTTPException(status_code=404, detail="Conexión no encontrada")
        client = LovableMcpClient()
        result = client.call_tool("list_projects", {}, token="")
        return {
            "id": connection_id,
            "authenticated": False,
            "status": result.get("status"),
            "error_code": result.get("error_code"),
        }

    @router.patch("/{connection_id}")
    async def update_connection(connection_id: str, body: dict):
        if "enabled" not in body:
            raise HTTPException(status_code=400, detail="enabled es obligatorio")
        platform.set_connection_enabled(connection_id, bool(body["enabled"]))
        return {"id": connection_id, "enabled": bool(body["enabled"])}

    return router
