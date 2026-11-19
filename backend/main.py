"""FastAPI application entry for the client acquisition dashboard."""

from backend.api.app_factory import create_app

app = create_app(start_worker=True)
