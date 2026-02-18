"""Runtime LLM client provider wiring."""

from __future__ import annotations

from apps.api.app.core.config import Settings
from apps.api.app.services.llm_extraction import (
    ExtractionClient,
    OpenAICompatibleTransport,
)


def build_extraction_client_from_settings(settings: Settings) -> ExtractionClient:
    transport = OpenAICompatibleTransport(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )
    return ExtractionClient(transport=transport, model=settings.llm_model)
