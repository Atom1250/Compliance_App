"""Provider interface for regulatory research engines."""

from __future__ import annotations

from typing import Protocol

from apps.api.app.services.regulatory_research.types import ResearchRequest, ResearchResponse


class ResearchProvider(Protocol):
    def query(self, req: ResearchRequest) -> ResearchResponse:
        """Return research response for the given request."""
