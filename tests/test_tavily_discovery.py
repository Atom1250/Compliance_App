from apps.api.app.services.tavily_discovery import (
    TavilyCandidate,
    download_discovery_candidate,
    search_tavily_documents,
)


def test_search_tavily_documents_keeps_non_pdf_candidates_for_download_validation(
    monkeypatch,
) -> None:
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
        reporting_year_start=None,
        reporting_year_end=None,
        api_key="test-key",
        base_url="https://api.tavily.com/search",
        timeout_seconds=5.0,
        max_results=5,
    )

    assert [candidate.url for candidate in candidates] == [
        "https://example.com/reports",
        "https://example.com/report.pdf",
    ]


def test_search_tavily_documents_uses_reporting_year_range_and_dedupes(monkeypatch) -> None:
    calls: list[str] = []

    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "results": [
                    {"title": "A", "url": "https://example.com/a.pdf", "score": 0.9},
                    {"title": "B", "url": "https://example.com/b.pdf", "score": 0.8},
                    {"title": "A2", "url": "https://example.com/a.pdf", "score": 0.95},
                ]
            }

    def _post(*args, **kwargs):
        calls.append(kwargs["json"]["query"])
        return _Resp()

    monkeypatch.setattr("apps.api.app.services.tavily_discovery.httpx.post", _post)
    candidates = search_tavily_documents(
        company_name="Nordea",
        reporting_year=2025,
        reporting_year_start=2024,
        reporting_year_end=2025,
        api_key="test-key",
        base_url="https://api.tavily.com/search",
        timeout_seconds=5.0,
        max_results=5,
    )
    assert len(calls) == 6
    assert [candidate.url for candidate in candidates] == [
        "https://example.com/a.pdf",
        "https://example.com/b.pdf",
    ]
    assert candidates[0].score == 0.95


def test_download_discovery_candidate_rejects_non_pdf_content(monkeypatch) -> None:
    class _Resp:
        content = b"<html>not pdf</html>"
        headers = {"content-type": "text/html"}
        url = "https://example.com/reports"

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr("apps.api.app.services.tavily_discovery.time.sleep", lambda *_: None)
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
