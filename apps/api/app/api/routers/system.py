"""System endpoints."""

from __future__ import annotations

import os
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from apps.api.app.core.config import get_settings
from apps.api.app.services.llm_health import (
    probe_openai_compatible,
    probe_openai_compatible_detailed,
)

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


class LLMProviderProbeResponse(BaseModel):
    provider: str
    base_url: str
    model: str
    reachable: bool | None
    parse_ok: bool | None
    detail: str


class LLMMultiHealthResponse(BaseModel):
    providers: list[LLMProviderProbeResponse]


def _provider_config(provider: Literal["local_lm_studio", "openai_cloud"]) -> tuple[str, str, str]:
    settings = get_settings()
    if provider == "openai_cloud":
        return (
            settings.openai_base_url,
            settings.openai_api_key or os.getenv("OPENAI_API_KEY", ""),
            settings.openai_model,
        )
    return (
        settings.llm_base_url,
        settings.llm_api_key,
        settings.llm_model,
    )


@router.get("/llm-health", response_model=LLMHealthResponse)
def llm_health(
    probe: bool = False,
    provider: Literal["local_lm_studio", "openai_cloud"] = "local_lm_studio",
) -> LLMHealthResponse:
    base_url, api_key, model = _provider_config(provider)

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


@router.get("/llm-health-matrix", response_model=LLMMultiHealthResponse)
def llm_health_matrix(probe: bool = True) -> LLMMultiHealthResponse:
    rows: list[LLMProviderProbeResponse] = []
    for provider in ["local_lm_studio", "openai_cloud"]:
        base_url, api_key, model = _provider_config(provider)
        if not probe:
            rows.append(
                LLMProviderProbeResponse(
                    provider=provider,
                    base_url=base_url,
                    model=model,
                    reachable=None,
                    parse_ok=None,
                    detail="probe_not_requested",
                )
            )
            continue
        if provider == "openai_cloud" and not api_key:
            rows.append(
                LLMProviderProbeResponse(
                    provider=provider,
                    base_url=base_url,
                    model=model,
                    reachable=False,
                    parse_ok=False,
                    detail="missing_api_key",
                )
            )
            continue
        reachable, parse_ok, detail = probe_openai_compatible_detailed(
            base_url=base_url,
            api_key=api_key,
            model=model,
        )
        rows.append(
            LLMProviderProbeResponse(
                provider=provider,
                base_url=base_url,
                model=model,
                reachable=reachable,
                parse_ok=parse_ok,
                detail=detail,
            )
        )
    return LLMMultiHealthResponse(providers=rows)
