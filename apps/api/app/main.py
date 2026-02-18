"""FastAPI application factory and app instance."""

from fastapi import FastAPI

from apps.api.app.api.routers.companies import router as companies_router
from apps.api.app.api.routers.documents import router as documents_router
from apps.api.app.api.routers.materiality import router as materiality_router
from apps.api.app.api.routers.retrieval import router as retrieval_router
from apps.api.app.api.routers.system import router as system_router
from apps.api.app.core.auth import validate_auth_configuration
from apps.api.app.core.config import get_settings


def create_app() -> FastAPI:
    """Create FastAPI app with deterministic configuration wiring."""
    settings = get_settings()
    validate_auth_configuration(
        security_enabled=settings.security_enabled,
        auth_api_keys=settings.auth_api_keys,
        auth_tenant_keys=settings.auth_tenant_keys,
    )
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(system_router)
    app.include_router(companies_router)
    app.include_router(documents_router)
    app.include_router(materiality_router)
    app.include_router(retrieval_router)
    return app


app = create_app()
