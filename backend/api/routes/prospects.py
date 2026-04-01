from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import h3
from backend.models.schemas import PatchProspectData, ResetCategoryAssignmentBody
from backend.domain.prospect import ProspectStatus
from backend.core.config import H3_RESOLUTION
from backend.generator.prompt_builder import build_demo_prompt
from backend.generator.account_manager import AccountManager
from backend.generator.service import GeneratorService
from backend.outreach.service import OutreachService
import asyncio


def create_prospects_router(db):
    router = APIRouter(prefix="/api", tags=["Prospects"])
    gen_service = GeneratorService(db)
    outreach_service = OutreachService(db)

    @router.get("/prospects")
    async def get_prospects(
        status: Optional[str] = None,
        category: Optional[str] = None,
        contacted: Optional[str] = None,
        name: Optional[str] = None,
        has_instagram: Optional[str] = None,
    ):
        try:
            is_contacted = None
            if contacted == "yes":
                is_contacted = True
            elif contacted == "no":
                is_contacted = False
            ig_only = None
            if has_instagram == "yes":
                ig_only = True
            elif has_instagram == "no":
                ig_only = False
            prospects = db.get_prospects(
                status=status,
                category=category,
                is_contacted=is_contacted,
                name_query=name,
                has_instagram=ig_only,
            )
            data = []
            for p in prospects:
                d = p.to_dict()
                d["lead_score"] = db.compute_lead_score(p)
                data.append(d)
            return data
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete("/prospects/{prospect_id}")
    async def delete_prospect(prospect_id: int):
        try:
            if prospect_id < 1:
                raise HTTPException(status_code=400, detail="ID inválido")
            if not db.delete_prospect_by_id(prospect_id):
                raise HTTPException(status_code=404, detail="Prospecto no encontrado")
            return {"message": "Prospecto eliminado"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/prospects")
    async def create_manual_prospect(data: dict):
        try:
            name = data.get("name", "").strip()
            category = data.get("category", "").strip()
            
            if not name or not category:
                raise HTTPException(status_code=400, detail="Name and category are required")
                
            from backend.domain.prospect import Prospect
            
            p = Prospect(
                name=name,
                category=category,
                address=data.get("address", ""),
                city=data.get("city", ""),
                phone=data.get("phone", ""),
                website=data.get("website", ""),
                rating=float(data.get("rating", 0.0)),
                reviews_count=int(data.get("reviews_count", 0)),
                maps_url=data.get("maps_url", ""),
                latitude=float(data.get("latitude", 0.0)),
                longitude=float(data.get("longitude", 0.0)),
                instagram_url=data.get("instagram_url", ""),
                instagram_handle=data.get("instagram_handle", ""),
                ig_followers=int(data.get("ig_followers", 0)),
                ig_bio=data.get("ig_bio", ""),
                ig_email=data.get("ig_email", ""),
                ig_phone=data.get("ig_phone", ""),
                ig_website=data.get("ig_website", ""),
                demo_url=data.get("demo_url", ""),
                demo_rating=float(data.get("demo_rating") or 0.0),
                screenshot_path=data.get("screenshot_path", ""),
                lovable_account_used=data.get("lovable_account_used", ""),
                prompt_used=data.get("prompt_used", ""),
                lovable_prompt=data.get("lovable_prompt", ""),
                status=data.get("status", ProspectStatus.SCRAPED.value),
                notes=data.get("notes", ""),
            )
            
            success = db.insert_prospect(p)
            if not success:
                raise HTTPException(status_code=409, detail="El prospecto ya existe")
                
            return {"message": "Prospecto creado manualmente", "prospect": p.to_dict()}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error creando prospecto: {str(e)}")

    @router.get("/prospects/random")
    async def get_random_prospect(status: str = "scraped", exclude: Optional[str] = None):
        try:
            p = db.get_random_prospect(status, exclude_name=exclude)
            if not p:
                return {"message": "No hay más prospectos por revisar"}
            return p
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/prospects/normalize-categories")
    async def normalize_categories():
        db.normalize_categories()
        return {"message": "Categorías normalizadas correctamente"}

    @router.post("/prospects/{name}/category")
    async def update_prospect_category(name: str, data: dict):
        try:
            new_category = data.get("category")
            if not new_category:
                raise HTTPException(status_code=400, detail="Falta categoría")

            prospects = db.get_prospects()
            p = next((x for x in prospects if x.name == name), None)
            if not p:
                raise HTTPException(status_code=404, detail="Prospecto no encontrado")

            db.update_status(
                p.name,
                p.address,
                status=ProspectStatus(p.status),
                category=new_category,
            )
            return {"message": "Categoría actualizada"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/categories")
    async def get_categories():
        try:
            return db.get_categories()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/cities")
    async def get_cities():
        try:
            return db.get_cities()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.patch("/prospects/{name}")
    async def patch_prospect(name: str, data: dict):
        try:
            prospects = db.get_prospects()
            p = next((x for x in prospects if x.name == name), None)
            if not p:
                raise HTTPException(status_code=404, detail="Prospecto no encontrado")

            if "demo_rating" in data:
                try:
                    rating = float(data["demo_rating"])
                except (TypeError, ValueError):
                    raise HTTPException(status_code=400, detail="demo_rating debe ser numérico")
                if rating < 0 or rating > 10:
                    raise HTTPException(status_code=400, detail="demo_rating debe estar entre 0 y 10")
                data["demo_rating"] = rating

            db.patch_prospect(p.name, p.address, data)
            return {"message": "Prospecto actualizado"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/hexagons")
    async def get_hexagons():
        try:
            prospects = db.get_prospects()
            hex_map = {}
            for p in prospects:
                if p.latitude and p.longitude:
                    try:
                        h3_id = h3.latlng_to_cell(
                            p.latitude, p.longitude, H3_RESOLUTION
                        )
                    except AttributeError:
                        h3_id = h3.geo_to_h3(p.latitude, p.longitude, H3_RESOLUTION)

                    if h3_id not in hex_map:
                        hex_map[h3_id] = {
                            "count": 0,
                            "status": "scraped",
                            "processed_count": 0,
                        }

                    hex_map[h3_id]["count"] += 1
                    processed_states = [
                        ProspectStatus.CONTACTED.value,
                        ProspectStatus.REJECTED.value,
                        ProspectStatus.CLIENT_REJECTED.value,
                        ProspectStatus.SKIPPED.value,
                        ProspectStatus.RESPONDED.value,
                    ]
                    if p.status in processed_states or p.is_contacted:
                        hex_map[h3_id]["processed_count"] += 1

            center_lat, center_lng = 6.2442, -75.5812
            try:
                center_h3 = h3.latlng_to_cell(center_lat, center_lng, H3_RESOLUTION)
                base_grid = h3.grid_disk(center_h3, 15)
            except AttributeError:
                center_h3 = h3.geo_to_h3(center_lat, center_lng, H3_RESOLUTION)
                base_grid = h3.k_ring(center_h3, 15)

            for h3_id in base_grid:
                if h3_id not in hex_map:
                    hex_map[h3_id] = {
                        "count": 0,
                        "status": "empty",
                        "processed_count": 0,
                    }

            features = []
            for h3_id, info in hex_map.items():
                try:
                    boundary = h3.cell_to_boundary(h3_id)
                except AttributeError:
                    boundary = h3.h3_to_geo_boundary(h3_id)

                if info["status"] == "empty":
                    status = "empty"
                else:
                    is_completed = (
                        info["count"] > 0 and info["count"] == info["processed_count"]
                    )
                    status = "completed" if is_completed else "scraped"

                features.append(
                    {
                        "id": h3_id,
                        "boundary": boundary,
                        "count": info["count"],
                        "processed_count": info["processed_count"],
                        "status": status,
                    }
                )
            return features
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/prospects/{name}/review")
    async def review_prospect(name: str, action: str):
        is_contacted = False
        if action == "accept":
            status = ProspectStatus.READY
        elif action == "contact":
            status = ProspectStatus.CONTACTED
            is_contacted = True
        else:
            status = ProspectStatus.REJECTED

        try:
            prospects = db.get_prospects()
            target = next((p for p in prospects if p.name == name), None)
            if not target:
                raise HTTPException(status_code=404, detail="Prospecto no encontrado")

            db.update_status(
                target.name, target.address, status=status, is_contacted=is_contacted
            )

            try:
                h3_id = h3.latlng_to_cell(
                    target.latitude, target.longitude, H3_RESOLUTION
                )
            except:
                h3_id = "N/A"
            print(
                f"[review] ACCION: {action .upper ()} lead '{target .name }' (H3: {h3_id })"
            )

            return {"status": "success", "new_status": status.value}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/prospects/{name}/automate")
    async def automate_full(name: str):
        """Dispara el flujo completo: Prompt + Lovable + Screenshot."""
        try:
            prospects = db.get_prospects()
            p = next((x for x in prospects if x.name == name), None)
            if not p:
                raise HTTPException(status_code=404, detail="Prospecto no encontrado")

            asyncio.create_task(gen_service.run_full_generation(p))

            return {
                "status": "pending",
                "message": "Generación completa iniciada. Mira los logs del servidor para el progreso.",
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/prospects/{name}/send-whatsapp")
    async def send_whatsapp(name: str):
        """Envía la propuesta vía WhatsApp."""
        try:
            prospects = db.get_prospects()
            p = next((x for x in prospects if x.name == name), None)
            if not p:
                raise HTTPException(status_code=404, detail="Prospecto no encontrado")

            asyncio.create_task(outreach_service.send_proposal(p))

            return {
                "status": "pending",
                "message": "Envío de WhatsApp iniciado. Abre el servidor para escanear el QR.",
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/prospects/{name}/generate")
    async def generate_prompt(name: str):
        """Genera el prompt para un prospecto específico."""
        try:
            prospects = db.get_prospects()
            p = next((x for x in prospects if x.name == name), None)
            if not p:
                raise HTTPException(status_code=404, detail="Prospecto no encontrado")

            prompt = build_demo_prompt(p)

            db.patch_prospect(p.name, p.address, {"prompt_used": prompt})

            return {
                "status": "success",
                "prompt": prompt,
                "message": "Prompt generado correctamente. Listo para enviar a ChatGPT.",
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/prompts")
    async def get_prompts():
        """Lista todos los prompts generados."""
        try:
            prospects = db.get_prospects()
            return [
                {"name": p.name, "prompt": p.prompt_used}
                for p in prospects
                if p.prompt_used
            ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/prospects/categories/reset-assignment")
    async def reset_category_assignment(body: ResetCategoryAssignmentBody):
        """Pone "Sin categoría" en todos los leads que tenían esta categoría."""
        try:
            if not body.category.strip():
                raise HTTPException(status_code=400, detail="Categoría vacía")
            db.delete_category(body.category)
            return {"message": "Asignaciones de categoría reiniciadas"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/stats")
    async def get_stats():
        try:
            return db.count_by_status()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/health")
    async def get_health():
        try:
            return db.get_health_snapshot()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/health/history")
    async def get_health_history(limit: int = 20):
        try:
            return db.get_recent_health_history(limit=limit)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/health/record")
    async def record_health():
        try:
            return db.record_health_snapshot()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router
