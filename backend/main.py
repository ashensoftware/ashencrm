"""FastAPI application entry for the client acquisition dashboard."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

from backend.api.routes.catalog import create_catalog_router
from backend.api.routes.prospects import create_prospects_router
from backend.api.routes.scrape import create_scrape_router
from backend.api.routes.screenshots import router as screenshots_router
from backend.core import config
from backend.services.scrape_service import ScrapeService
from backend.database.db import Database


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.setup_windows_asyncio()
    yield


app = FastAPI(title="Client Acquisition Dashboard", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database()
scrape_service = ScrapeService(db)
app.include_router(create_prospects_router(db))
app.include_router(create_catalog_router(db))
app.include_router(create_scrape_router(scrape_service))
app.include_router(screenshots_router)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
dist_dir = FRONTEND_DIR / "dist"

app.mount(
    "/",
    StaticFiles(
        directory=str(dist_dir if dist_dir.exists() else FRONTEND_DIR), html=True
    ),
    name="frontend",
)
