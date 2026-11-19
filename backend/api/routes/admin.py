from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import require_role
from backend.core.auth import Principal, TokenAuthenticator
from backend.services.app_settings_service import (
    patch_body_to_storage,
    typed_public_settings,
)


def create_admin_router(
    db, authenticator: TokenAuthenticator, *, sql_console_enabled: bool
):
    router = APIRouter(prefix="/api/admin", tags=["Admin"])
    require_admin = require_role(authenticator, "admin")

    @router.get("/settings")
    async def get_settings(_: Principal = Depends(require_admin)):
        try:
            return typed_public_settings(db)
        except (KeyError, ValueError) as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.patch("/settings")
    async def patch_settings(body: dict, _: Principal = Depends(require_admin)):
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
    async def sql_console_status(_: Principal = Depends(require_admin)):
        return {"enabled": sql_console_enabled}

    @router.post("/sql")
    async def run_sql(body: dict, _: Principal = Depends(require_admin)):
        if not sql_console_enabled:
            raise HTTPException(status_code=404, detail="Consola SQL no disponible")
        sql = body.get("sql")
        if not isinstance(sql, str):
            raise HTTPException(
                status_code=400, detail='Se requiere un campo "sql" (texto)'
            )
        try:
            return db.execute_sql_console(sql)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return router
