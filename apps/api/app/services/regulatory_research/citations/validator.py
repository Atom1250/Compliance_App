"""Citation policy validator for regulatory research responses."""

from __future__ import annotations

from dataclasses import dataclass

from apps.api.app.services.regulatory_research.citations.errors import CitationValidationError
from apps.api.app.services.regulatory_research.types import ResearchResponse


@dataclass(frozen=True)
class CitationValidationResult:
    can_persist: bool


def validate_citations(resp: ResearchResponse, *, strict: bool) -> CitationValidationResult:
    citations = resp.citations
    if strict:
        if not citations:
            raise CitationValidationError(
                "Strict citations mode requires at least one citation (source_title + locator/url)."
            )
        for item in citations:
            if not item.source_title.strip():
                raise CitationValidationError(
                    "Strict citations mode requires source_title for every citation."
                )
            if not ((item.locator and item.locator.strip()) or (item.url and item.url.strip())):
                raise CitationValidationError(
                    "Strict citations mode requires locator or url for every citation."
                )
        return CitationValidationResult(can_persist=True)

    if not citations:
        return CitationValidationResult(can_persist=False)

    for item in citations:
        if not item.source_title.strip():
            return CitationValidationResult(can_persist=False)
        if not ((item.locator and item.locator.strip()) or (item.url and item.url.strip())):
            return CitationValidationResult(can_persist=False)
    return CitationValidationResult(can_persist=True)
