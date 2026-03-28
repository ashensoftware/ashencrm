from fastapi import APIRouter, HTTPException

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

    return router
