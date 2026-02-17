"""System endpoints."""

from fastapi import APIRouter

from apps.api.app.core.config import get_settings

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness endpoint."""
    return {"status": "ok"}


@router.get("/version")
def version() -> dict[str, str]:
    """Return application version from settings."""
    settings = get_settings()
    return {"version": settings.app_version}
