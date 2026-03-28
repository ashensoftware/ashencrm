from fastapi import APIRouter, BackgroundTasks
from backend.models.schemas import ScrapeRequest
from backend.core.logger import get_logs


def create_scrape_router(scrape_service):
    router = APIRouter(prefix="/api", tags=["Scraping"])

    @router.get("/scrape-logs")
    async def get_scrape_logs():
        return get_logs()

    @router.post("/scrape-interactive")
    async def trigger_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
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
