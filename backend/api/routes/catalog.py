from fastapi import APIRouter, HTTPException
from backend.models.schemas import CatalogCategory


def create_catalog_router(db):
    router = APIRouter(prefix="/api/catalog", tags=["Catalog"])

    @router.get("/categories")
    async def get_catalog_categories():
        return db.get_catalog_categories()

    @router.post("/categories")
    async def add_catalog_category(cat: CatalogCategory):
        db.add_catalog_category(cat.name, cat.label, cat.icon)
        return {"message": "Categoría añadida al catálogo"}

    @router.delete("/categories/{name}")
    async def delete_catalog_category(name: str):
        db.delete_catalog_category(name)
        return {"message": "Categoría eliminada del catálogo"}

    return router
