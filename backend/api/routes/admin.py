from fastapi import APIRouter, HTTPException

from backend.config.settings import settings
from backend.services.app_settings_service import (
    patch_body_to_storage,
    typed_public_settings,
)


def create_admin_router(db):
    router = APIRouter(prefix="/api/admin", tags=["Admin"])

    @router.get("/settings")
    async def get_settings():
        try:
            return typed_public_settings(db)
        except (KeyError, ValueError) as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.patch("/settings")
    async def patch_settings(body: dict):
        try:
            to_store = patch_body_to_storage(body)
            if not to_store:
                return typed_public_settings(db)
            db.upsert_app_settings(to_store)
            return typed_public_settings(db)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/sql/status")
    async def sql_console_status():
        return {"enabled": settings.sql_console_enabled}

    @router.post("/sql")
    async def run_sql(body: dict):
        if not settings.sql_console_enabled:
            raise HTTPException(
                status_code=403,
                detail="Consola SQL deshabilitada. En .env usa ALLOW_SQL_CONSOLE=1 (por defecto está activa en local).",
            )
        sql = body.get("sql")
        if not isinstance(sql, str):
            raise HTTPException(status_code=400, detail='Se requiere un campo "sql" (texto)')
        try:
            return db.execute_sql_console(sql)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return router
