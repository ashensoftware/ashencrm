"""Ejecuciones durables del pipeline. El HTTP solo encola."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from backend.infrastructure.persistence.platform_repository import STAGES, PlatformRepository


def create_pipeline_router(platform: PlatformRepository) -> APIRouter:
    router = APIRouter(prefix="/api/v1/pipeline-runs", tags=["Pipeline"])

    def _actor(request: Request) -> str:
        principal = getattr(request.state, "principal", None)
        if principal is not None:
            return principal.subject
        return "authenticated"

    @router.post("")
    async def create_run(request: Request, body: dict | None = None):
        payload = body or {}
        campaign_id = str(payload.get("campaign_id") or "").strip()
        if not campaign_id:
            raise HTTPException(status_code=400, detail="campaign_id es obligatorio")
        key = request.headers.get("idempotency-key")
        created = platform.create_run(
            campaign_id=campaign_id,
            requested_by=_actor(request),
            idempotency_key=key.strip() if key else None,
            config={k: v for k, v in payload.items() if k != "access_token"},
            stages=STAGES,
        )
        return created

    @router.get("/{run_id}")
    async def get_run(run_id: str):
        found = platform.get_run(run_id)
        if not found:
            raise HTTPException(status_code=404, detail="Ejecución no encontrada")
        found["events"] = platform.events(run_id)
        return found

    @router.post("/{run_id}/pause")
    async def pause_run(run_id: str):
        return _transition(platform, run_id, "paused")

    @router.post("/{run_id}/resume")
    async def resume_run(run_id: str):
        return _transition(platform, run_id, "running")

    @router.post("/{run_id}/cancel")
    async def cancel_run(run_id: str):
        return _transition(platform, run_id, "cancelled")

    @router.post("/{run_id}/retry-failed")
    async def retry_failed(run_id: str):
        if platform.get_run(run_id) is None:
            raise HTTPException(status_code=404, detail="Ejecución no encontrada")
        count = platform.retry_failed(run_id)
        return {"retried": count}

    return router


def _transition(platform: PlatformRepository, run_id: str, status: str) -> dict:
    try:
        platform.set_run_status(run_id, status)
    except KeyError:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada") from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"id": run_id, "status": status}
