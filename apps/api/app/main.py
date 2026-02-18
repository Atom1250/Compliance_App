"""FastAPI application factory and app instance."""

from fastapi import FastAPI

from apps.api.app.api.routers.documents import router as documents_router
from apps.api.app.api.routers.materiality import router as materiality_router
from apps.api.app.api.routers.retrieval import router as retrieval_router
from apps.api.app.api.routers.system import router as system_router
from apps.api.app.core.config import get_settings


def create_app() -> FastAPI:
    """Create FastAPI app with deterministic configuration wiring."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(system_router)
    app.include_router(documents_router)
    app.include_router(materiality_router)
    app.include_router(retrieval_router)
    return app


app = create_app()
