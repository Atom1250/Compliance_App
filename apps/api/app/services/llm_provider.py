"""Runtime LLM client provider wiring."""

from __future__ import annotations

import os

from apps.api.app.core.config import Settings
from apps.api.app.services.llm_extraction import (
    ExtractionClient,
    OpenAICompatibleTransport,
)

SUPPORTED_LLM_PROVIDERS = {"local_lm_studio", "openai_cloud"}


def build_extraction_client_from_settings(
    settings: Settings, *, provider: str = "local_lm_studio"
) -> ExtractionClient:
    if provider not in SUPPORTED_LLM_PROVIDERS:
        raise ValueError(f"unsupported llm provider: {provider}")

    if provider == "openai_cloud":
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("openai_api_key is required for openai_cloud provider")
        if not settings.openai_base_url:
            raise ValueError("openai_base_url is required for openai_cloud provider")
        if not settings.openai_model:
            raise ValueError("openai_model is required for openai_cloud provider")
        transport = OpenAICompatibleTransport(
            base_url=settings.openai_base_url,
            api_key=api_key,
        )
        return ExtractionClient(transport=transport, model=settings.openai_model)

    if not settings.llm_base_url:
        raise ValueError("llm_base_url is required for local_lm_studio provider")
    if not settings.llm_model:
        raise ValueError("llm_model is required for local_lm_studio provider")
    transport = OpenAICompatibleTransport(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )
    return ExtractionClient(transport=transport, model=settings.llm_model)
