"""CRUD de clientes post-venta, reuniones y cotización PDF."""

from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.config.settings import settings
from backend.core.google_maps_url import parse_google_maps_link

CLIENT_STAGES = frozenset(
    {
        "quote_sent",
        "meetings",
        "payment_received",
        "contract",
        "in_development",
        "qa_staging",
        "delivered",
        "on_hold",
        "closed_lost",
    }
)

MAX_QUOTE_PDF_BYTES = 15 * 1024 * 1024


def _clients_upload_dir() -> Path:
    d = settings.data_dir / "client_uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def create_clients_router(db):
    router = APIRouter(prefix="/api/clients", tags=["Clients"])

    @router.get("")
    async def list_clients():
        try:
            return db.list_clients()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/map-markers")
    async def clients_map_markers():
        try:
            return db.list_clients_map_markers()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/parse-maps-url")
    async def parse_maps_url(body: dict):
        """Resuelve enlaces cortos y devuelve lat/lng + nombre sugerido desde la URL."""
        try:
            url = (body.get("url") or "").strip()
            return parse_google_maps_link(url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("")
    async def create_client(body: dict):
        try:
            name = (body.get("display_name") or "").strip()
            if not name:
                raise HTTPException(status_code=400, detail="display_name es obligatorio")
            stage = body.get("stage", "quote_sent")
            if stage not in CLIENT_STAGES:
                raise HTTPException(status_code=400, detail="stage inválido")
            cid = db.insert_client(body)
            row = db.get_client(cid)
            return row
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/{client_id:int}")
    async def get_client(client_id: int):
        try:
            row = db.get_client(client_id)
            if not row:
                raise HTTPException(status_code=404, detail="Cliente no encontrado")
            meetings = db.list_client_meetings(client_id)
            return {**row, "meetings": meetings}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.patch("/{client_id:int}")
    async def patch_client(client_id: int, body: dict):
        try:
            if not db.get_client(client_id):
                raise HTTPException(status_code=404, detail="Cliente no encontrado")
            if "stage" in body and body["stage"] not in CLIENT_STAGES:
                raise HTTPException(status_code=400, detail="stage inválido")
            for k in ("contract_required", "contract_skipped"):
                if k in body and isinstance(body[k], bool):
                    body[k] = 1 if body[k] else 0
            db.update_client(client_id, body)
            row = db.get_client(client_id)
            meetings = db.list_client_meetings(client_id)
            return {**row, "meetings": meetings}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete("/{client_id:int}")
    async def delete_client(client_id: int):
        try:
            if not db.get_client(client_id):
                raise HTTPException(status_code=404, detail="Cliente no encontrado")
            c = db.get_client(client_id)
            if c and c.get("quote_pdf_path"):
                p = Path(c["quote_pdf_path"])
                if p.is_file():
                    try:
                        p.unlink()
                    except OSError:
                        pass
            db.delete_client(client_id)
            return {"ok": True}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/from-prospect/{prospect_name:path}")
    async def from_prospect(prospect_name: str):
        try:
            cid = db.create_client_from_prospect_name(prospect_name)
            row = db.get_client(cid)
            meetings = db.list_client_meetings(cid)
            return {**row, "meetings": meetings}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/{client_id:int}/quote")
    async def upload_quote_pdf(
        client_id: int,
        file: UploadFile = File(...),
        quote_amount: Optional[float] = Form(None),
        quote_currency: Optional[str] = Form(None),
        estimated_delivery_at: Optional[str] = Form(None),
    ):
        try:
            c = db.get_client(client_id)
            if not c:
                raise HTTPException(status_code=404, detail="Cliente no encontrado")
            if not file.filename or not file.filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail="Solo se acepta PDF")
            raw = await file.read()
            if len(raw) > MAX_QUOTE_PDF_BYTES:
                raise HTTPException(status_code=400, detail="PDF demasiado grande (máx 15MB)")
            sub = _clients_upload_dir() / str(client_id)
            sub.mkdir(parents=True, exist_ok=True)
            dest = sub / "quote.pdf"
            dest.write_bytes(raw)
            from datetime import datetime

            patch: dict[str, Any] = {
                "quote_pdf_path": str(dest),
                "quoted_at": datetime.now().isoformat(),
            }
            if quote_amount is not None:
                patch["quote_amount"] = quote_amount
            if quote_currency:
                patch["quote_currency"] = quote_currency
            if estimated_delivery_at:
                patch["estimated_delivery_at"] = estimated_delivery_at
            db.update_client(client_id, patch)
            row = db.get_client(client_id)
            meetings = db.list_client_meetings(client_id)
            return {**row, "meetings": meetings}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/{client_id:int}/quote-pdf")
    async def get_quote_pdf(client_id: int):
        c = db.get_client(client_id)
        if not c:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        path = c.get("quote_pdf_path") or ""
        p = Path(path) if path else None
        if not p or not p.is_file():
            raise HTTPException(status_code=404, detail="Sin cotización PDF")
        return FileResponse(p, media_type="application/pdf", filename="cotizacion.pdf")

    @router.post("/{client_id:int}/meetings")
    async def add_meeting(client_id: int, body: dict):
        if not db.get_client(client_id):
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        mid = db.insert_client_meeting(client_id, body)
        m = db.get_client_meeting(mid)
        return m or {"id": mid}

    @router.patch("/meetings/{meeting_id:int}")
    async def patch_meeting(meeting_id: int, body: dict):
        db.update_client_meeting(meeting_id, body)
        row = db.get_client_meeting(meeting_id)
        return row or {}

    @router.delete("/meetings/{meeting_id:int}")
    async def del_meeting(meeting_id: int):
        db.delete_client_meeting(meeting_id)
        return {"ok": True}

    return router
