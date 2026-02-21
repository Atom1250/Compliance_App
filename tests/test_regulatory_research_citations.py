import pytest

from apps.api.app.services.regulatory_research.citations.errors import CitationValidationError
from apps.api.app.services.regulatory_research.citations.validator import validate_citations
from apps.api.app.services.regulatory_research.types import Citation, ResearchResponse


def _response(citations: list[Citation]) -> ResearchResponse:
    return ResearchResponse(
        answer_markdown="answer",
        citations=citations,
        provider="notebooklm",
        confidence=0.8,
        latency_ms=12,
        request_hash="h" * 64,
    )


def test_strict_citations_requires_at_least_one() -> None:
    with pytest.raises(CitationValidationError):
        validate_citations(_response([]), strict=True)


def test_strict_citations_requires_locator_or_url() -> None:
    with pytest.raises(CitationValidationError):
        validate_citations(
            _response([Citation(source_title="ESRS", locator=None, url=None)]),
            strict=True,
        )


def test_strict_citations_valid_passes() -> None:
    result = validate_citations(
        _response([Citation(source_title="ESRS", locator="E1-1", url=None)]),
        strict=True,
    )
    assert result.can_persist is True


def test_non_strict_empty_citations_disallow_persist() -> None:
    result = validate_citations(_response([]), strict=False)
    assert result.can_persist is False
