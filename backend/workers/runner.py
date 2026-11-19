"""Worker que reclama pasos durables. No envía WhatsApp ni llama a proveedores de pago.

La cola vive en SQLite. Si el proceso muere, el siguiente arranque vuelve a
reclamar los pasos cuyo heartbeat venció.
"""

from __future__ import annotations

import threading
from typing import Any, Callable

from backend.domain.identity import canonical_domain, phone_e164
from backend.infrastructure.persistence.platform_repository import PlatformRepository

Handler = Callable[[dict[str, Any]], dict[str, Any]]

_DEFAULT_PLACES = (
    {
        "provider": "simulated",
        "external_id": "sim-cafe-norte",
        "display_name": "Cafe Norte",
        "domain": "https://www.cafenorte.example",
        "phone": "3001112233",
    },
)


def build_handlers(store: PlatformRepository) -> dict[str, Handler]:
    def discover(step: dict[str, Any]) -> dict[str, Any]:
        run = store.get_run(step["run_id"])
        config = (run or {}).get("run", {}).get("config", {})
        places = config.get("places") or list(_DEFAULT_PLACES)
        for place in places:
            external_id = str(place.get("external_id") or "").strip()
            if not external_id:
                continue
            store.upsert_business(
                provider=str(place.get("provider") or "simulated"),
                external_id=external_id,
                display_name=str(place.get("display_name") or external_id),
                domain=canonical_domain(place.get("domain")),
                phone_e164=phone_e164(place.get("phone")),
                confidence=float(place.get("confidence") or 0.6),
            )
        return {"status": "succeeded", "count": len(places)}

    def passthrough(_step: dict[str, Any]) -> dict[str, Any]:
        return {"status": "succeeded"}

    def generate(step: dict[str, Any]) -> dict[str, Any]:
        run = store.get_run(step["run_id"])
        config = (run or {}).get("run", {}).get("config", {})
        artifact = config.get("verified_artifact")
        if not isinstance(artifact, dict):
            return {
                "status": "incomplete",
                "error_code": "artifact_missing",
                "message": "No hay URL verificada ni captura del servidor",
            }
        return {"status": "succeeded", "artifact": {"present": True}}

    def prepare_outreach(step: dict[str, Any]) -> dict[str, Any]:
        run = store.get_run(step["run_id"])
        config = (run or {}).get("run", {}).get("config", {})
        contact = config.get("contact")
        decision = store.outreach_eligibility(
            contact if isinstance(contact, str) else None,
            "whatsapp",
            live_allowed=False,
        )
        store.record_outreach(
            business_id=None,
            campaign_id=(run or {}).get("run", {}).get("campaign_id", ""),
            status=decision,
            dry_run=True,
            preview="preparado en dry-run",
        )
        return {"status": "succeeded", "eligibility": decision, "delivered": False}

    return {
        "discover": discover,
        "normalize": passthrough,
        "dedupe": passthrough,
        "enrich": passthrough,
        "score": passthrough,
        "generate": generate,
        "validate": passthrough,
        "prepare_outreach": prepare_outreach,
    }


def process_once(store: PlatformRepository, worker_id: str = "worker") -> dict[str, Any] | None:
    step = store.claim_step(worker_id)
    if step is None:
        return None
    handler = build_handlers(store).get(step["stage"])
    try:
        if handler is None:
            result = {"status": "failed", "error_code": "unknown_stage", "message": "Etapa desconocida"}
        else:
            result = handler(step)
    except Exception:
        result = {"status": "failed", "error_code": "handler_error", "message": "La etapa falló"}
    store.complete_step(step["id"], result)
    return step


def drain(store: PlatformRepository, *, limit: int = 50, worker_id: str = "worker") -> int:
    done = 0
    for _ in range(limit):
        if process_once(store, worker_id) is None:
            break
        done += 1
    return done


def worker_loop(store: PlatformRepository, stop: threading.Event, worker_id: str = "worker") -> None:
    while not stop.is_set():
        processed = None
        try:
            processed = process_once(store, worker_id)
        except Exception:
            processed = None
        if processed is None:
            stop.wait(1)
