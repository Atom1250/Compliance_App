from apps.api.app.services.tavily_discovery import (
    TavilyCandidate,
    download_discovery_candidate,
    search_tavily_documents,
)


def test_search_tavily_documents_filters_non_pdf(monkeypatch) -> None:
    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "results": [
                    {
                        "title": "Annual Report",
                        "url": "https://example.com/report.pdf",
                        "score": 0.9,
                    },
                    {"title": "Listing Page", "url": "https://example.com/reports", "score": 0.95},
                ]
            }

    monkeypatch.setattr(
        "apps.api.app.services.tavily_discovery.httpx.post",
        lambda *args, **kwargs: _Resp(),
    )

    candidates = search_tavily_documents(
        company_name="Nordea",
        reporting_year=2025,
        api_key="test-key",
        base_url="https://api.tavily.com/search",
        timeout_seconds=5.0,
        max_results=5,
    )

    assert [candidate.url for candidate in candidates] == ["https://example.com/report.pdf"]


def test_search_tavily_documents_has_deterministic_tie_break(monkeypatch) -> None:
    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "results": [
                    {"title": "B", "url": "https://example.com/b.pdf", "score": 0.9},
                    {"title": "A", "url": "https://example.com/a.pdf", "score": 0.9},
                    {"title": "C", "url": "https://example.com/c.PDF", "score": 0.9},
                ]
            }

    monkeypatch.setattr(
        "apps.api.app.services.tavily_discovery.httpx.post",
        lambda *args, **kwargs: _Resp(),
    )
    candidates = search_tavily_documents(
        company_name="Nordea",
        reporting_year=2025,
        api_key="test-key",
        base_url="https://api.tavily.com/search",
        timeout_seconds=5.0,
        max_results=5,
    )
    assert [candidate.url for candidate in candidates] == [
        "https://example.com/a.pdf",
        "https://example.com/b.pdf",
        "https://example.com/c.PDF",
    ]


def test_download_discovery_candidate_rejects_non_pdf_content(monkeypatch) -> None:
    class _Resp:
        content = b"<html>not pdf</html>"
        headers = {"content-type": "text/html"}
        url = "https://example.com/reports"

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(
        "apps.api.app.services.tavily_discovery.httpx.get",
        lambda *args, **kwargs: _Resp(),
    )

    candidate = TavilyCandidate(title="Reports", url="https://example.com/reports", score=0.8)
    try:
        download_discovery_candidate(
            candidate=candidate,
            timeout_seconds=5.0,
            max_document_bytes=1024,
        )
        assert False, "expected ValueError"
    except ValueError as exc:
        assert str(exc) == "downloaded content is not a PDF"
