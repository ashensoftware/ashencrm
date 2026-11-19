from fastapi import APIRouter, BackgroundTasks, HTTPException
from backend.models.schemas import ScrapeRequest
from backend.config.settings import settings
from backend.core.logger import get_logs
from backend.core.security_policy import legacy_maps_scraper_enabled


def create_scrape_router(scrape_service):
    router = APIRouter(prefix="/api", tags=["Scraping"])

    @router.get("/scrape-logs")
    async def get_scrape_logs():
        return get_logs()

    @router.post("/scrape-interactive")
    async def trigger_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
        if not legacy_maps_scraper_enabled(
            settings.app_env, settings.legacy_maps_scraper_enabled
        ):
            raise HTTPException(
                status_code=409,
                detail="El scraper DOM de mapas está desactivado. Usa el pipeline.",
            )
        background_tasks.add_task(
            scrape_service.threaded_scrape_launcher,
            request.category,
            request.city,
            request.limit,
            request.lat,
            request.lon,
        )
        return {"message": "Scrape iniciado en segundo plano"}

    return router
