"""Deterministic stub provider for tests and offline workflows."""

from __future__ import annotations

from apps.api.app.services.regulatory_research.hash import compute_request_hash
from apps.api.app.services.regulatory_research.provider import ResearchProvider
from apps.api.app.services.regulatory_research.types import (
    Citation,
    ResearchRequest,
    ResearchResponse,
)


class StubResearchProvider(ResearchProvider):
    def query(self, req: ResearchRequest) -> ResearchResponse:
        request_hash = compute_request_hash(req)
        answer = (
            f"Stub research response for `{req.corpus_key}` in `{req.mode}` mode.\n\n"
            f"Request hash: `{request_hash}`"
        )
        citations = [
            Citation(
                source_title="Stub Regulatory Source A",
                locator="Section 1",
                url="https://example.com/reg-a",
                quote="Stub citation for deterministic test flow.",
            ),
            Citation(
                source_title="Stub Regulatory Source B",
                locator="Annex B",
                url="https://example.com/reg-b",
                quote="Secondary support citation.",
            ),
        ]
        return ResearchResponse(
            answer_markdown=answer,
            citations=citations,
            provider="stub",
            latency_ms=0,
            request_hash=request_hash,
            confidence=1.0,
            can_persist=True,
        )
