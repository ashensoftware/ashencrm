from fastapi import APIRouter, HTTPException
from backend.models.schemas import CatalogCategory, RenameCategoryRequest, PatchCatalogCategory


def create_catalog_router(db):
    router = APIRouter(prefix="/api/catalog", tags=["Catalog"])

    @router.get("/categories")
    async def get_catalog_categories():
        return db.get_catalog_categories()

    @router.post("/categories")
    async def add_catalog_category(cat: CatalogCategory):
        db.add_catalog_category(cat.name, cat.label, cat.icon)
        return {"message": "Categoría añadida al catálogo"}

    @router.put("/categories/rename")
    async def rename_catalog_category(data: RenameCategoryRequest):
        try:
            db.rename_category_globally(data.old_name, data.new_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"message": "Categoría renombrada"}

    @router.patch("/categories/{name}")
    async def patch_catalog_category(name: str, body: PatchCatalogCategory):
        if body.label is None and body.icon is None:
            raise HTTPException(status_code=400, detail="Envía label o icon")
        ok = db.patch_catalog_category(name, label=body.label, icon=body.icon)
        if not ok:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        return {"message": "Categoría actualizada"}

    @router.delete("/categories/{name}")
    async def delete_catalog_category(name: str):
        db.delete_catalog_category(name)
        return {"message": "Categoría eliminada del catálogo"}

    return router
