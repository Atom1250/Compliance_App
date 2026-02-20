"""Factory for regulatory research service/provider selection."""

from __future__ import annotations

from apps.api.app.core.config import Settings
from apps.api.app.integrations.notebooklm.provider import build_notebooklm_provider
from apps.api.app.services.regulatory_research.providers.stub import StubResearchProvider
from apps.api.app.services.regulatory_research.service import RegulatoryResearchService


def build_regulatory_research_service(settings: Settings) -> RegulatoryResearchService:
    if settings.feature_notebooklm_enabled:
        provider = build_notebooklm_provider(settings)
        provider_name = "notebooklm"
    else:
        provider = StubResearchProvider()
        provider_name = "stub"
    return RegulatoryResearchService(
        provider=provider,
        settings=settings,
        provider_name=provider_name,
    )
