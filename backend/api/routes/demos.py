"""Validación de una URL de demo pegada a mano. Nunca marca demo_created."""

from __future__ import annotations

from fastapi import APIRouter

from backend.core.ssrf import is_safe_public_url
from backend.generator.verification import is_acceptable_demo_url, is_placeholder_demo_url


def create_demo_router() -> APIRouter:
    router = APIRouter(prefix="/api/demos", tags=["Demos"])

    @router.post("/validate")
    async def validate_demo(body: dict):
        url = body.get("url") if isinstance(body, dict) else None
        if is_placeholder_demo_url(url if isinstance(url, str) else None):
            return {
                "success": False,
                "verified": False,
                "status": "incomplete",
                "detail": "La URL es un placeholder y no cuenta como demo",
            }
        if not isinstance(url, str) or not is_safe_public_url(url):
            return {
                "success": False,
                "verified": False,
                "status": "incomplete",
                "detail": "La URL no es un destino público permitido",
            }
        if not is_acceptable_demo_url(url):
            return {
                "success": False,
                "verified": False,
                "status": "incomplete",
                "detail": "La URL no es un proyecto Lovable verificable",
            }
        return {
            "success": False,
            "verified": False,
            "status": "incomplete",
            "detail": "Falta una captura generada por el servidor. La URL no se marcó como demo.",
        }

    return router
