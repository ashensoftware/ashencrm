"""Capacidades de Lovable tomadas de la documentación pública de MCP.

No se inventan endpoints. La automatización de navegador no forma parte de este cliente.
Documentación: https://docs.lovable.dev/integrations/lovable-mcp-server
"""

from __future__ import annotations

from typing import Any, Callable

MCP_ENDPOINT = "https://mcp.lovable.dev"
DOCUMENTED_TOOLS = (
    "create_project",
    "get_project",
    "deploy_project",
    "list_projects",
    "send_message",
)
API_KEY_SUPPORTED = False


def documented_capabilities() -> dict[str, Any]:
    return {
        "mcp_endpoint": MCP_ENDPOINT,
        "auth": "oauth",
        "api_key_supported": API_KEY_SUPPORTED,
        "tools": list(DOCUMENTED_TOOLS),
        "browser_automation": False,
        "note": (
            "OAuth es el único método documentado. deploy_project puede devolver una URL "
            "sin que eso confirme el despliegue; hay que verificar con get_project."
        ),
    }


class LovableMcpClient:
    """JSON-RPC tools/call. El transporte se inyecta en pruebas; no hay red por defecto."""

    def __init__(self, transport: Callable[[dict], dict] | None = None):
        self._transport = transport

    def call_tool(self, name: str, arguments: dict, token: str) -> dict:
        if name not in DOCUMENTED_TOOLS:
            return {"ok": False, "status": "unsupported_tool", "error_code": "unsupported_tool"}
        if not token:
            return {
                "ok": False,
                "status": "MANUAL_ACTION_REQUIRED",
                "error_code": "oauth_required",
                "capabilities": documented_capabilities(),
            }
        if self._transport is None:
            return {
                "ok": False,
                "status": "BLOCKED_EXTERNAL",
                "error_code": "oauth_client_not_configured",
                "capabilities": documented_capabilities(),
            }
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        result = self._transport(payload)
        if not isinstance(result, dict):
            return {"ok": False, "status": "incomplete", "error_code": "invalid_provider_response"}
        return result
