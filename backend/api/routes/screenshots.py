"""Serve prospect screenshots from data/screenshots."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parents[5]
SCREENSHOTS_DIR = ROOT / "data" / "screenshots"

router = APIRouter(prefix="/api/screenshots", tags=["Screenshots"])


@router.get("/{filename:path}")
async def serve_screenshot(filename: str):
    """Serve screenshot by filename (no path traversal)."""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=404, detail="Not found")
    safe_name = Path(filename).name
    path = SCREENSHOTS_DIR / safe_name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path)
