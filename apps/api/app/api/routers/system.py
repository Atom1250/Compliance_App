"""System endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from apps.api.app.core.config import get_settings
from apps.api.app.services.llm_health import probe_local_llm

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


class LLMHealthResponse(BaseModel):
    base_url: str
    model: str
    reachable: bool | None
    detail: str


@router.get("/llm-health", response_model=LLMHealthResponse)
def llm_health(probe: bool = False) -> LLMHealthResponse:
    settings = get_settings()
    if not probe:
        return LLMHealthResponse(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            reachable=None,
            detail="probe_not_requested",
        )

    reachable, detail = probe_local_llm(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
    )
    return LLMHealthResponse(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        reachable=reachable,
        detail=detail,
    )
