"""System endpoints."""

from __future__ import annotations

import os
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from apps.api.app.core.config import get_settings
from apps.api.app.services.llm_health import probe_openai_compatible

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
    provider: str
    base_url: str
    model: str
    reachable: bool | None
    detail: str


@router.get("/llm-health", response_model=LLMHealthResponse)
def llm_health(
    probe: bool = False,
    provider: Literal["local_lm_studio", "openai_cloud"] = "local_lm_studio",
) -> LLMHealthResponse:
    settings = get_settings()
    if provider == "openai_cloud":
        base_url = settings.openai_base_url
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")
        model = settings.openai_model
    else:
        base_url = settings.llm_base_url
        api_key = settings.llm_api_key
        model = settings.llm_model

    if not probe:
        return LLMHealthResponse(
            provider=provider,
            base_url=base_url,
            model=model,
            reachable=None,
            detail="probe_not_requested",
        )

    reachable, detail = probe_openai_compatible(
        base_url=base_url,
        api_key=api_key,
        model=model,
    )
    return LLMHealthResponse(
        provider=provider,
        base_url=base_url,
        model=model,
        reachable=reachable,
        detail=detail,
    )
