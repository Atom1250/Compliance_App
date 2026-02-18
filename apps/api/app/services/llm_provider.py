"""Runtime LLM client provider wiring."""

from __future__ import annotations

import os

from apps.api.app.core.config import Settings
from apps.api.app.services.llm_extraction import (
    ExtractionClient,
    OpenAICompatibleTransport,
)


def build_extraction_client_from_settings(
    settings: Settings, *, provider: str = "local_lm_studio"
) -> ExtractionClient:
    if provider == "openai_cloud":
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("openai_api_key is required for openai_cloud provider")
        transport = OpenAICompatibleTransport(
            base_url=settings.openai_base_url,
            api_key=api_key,
        )
        return ExtractionClient(transport=transport, model=settings.openai_model)

    transport = OpenAICompatibleTransport(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )
    return ExtractionClient(transport=transport, model=settings.llm_model)
