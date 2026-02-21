import httpx

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


def test_download_discovery_candidate_retries_host_variant_on_403(monkeypatch) -> None:
    called_urls: list[str] = []

    class _RespOk:
        content = b"%PDF-1.7 mock"
        headers = {"content-type": "application/pdf"}
        url = "https://example.com/report.pdf"

        def raise_for_status(self) -> None:
            return None

    class _RespForbidden:
        content = b""
        headers = {"content-type": "text/html"}
        url = "https://www.example.com/report.pdf"

        def raise_for_status(self) -> None:
            request = httpx.Request("GET", self.url)
            response = httpx.Response(403, request=request)
            raise httpx.HTTPStatusError("forbidden", request=request, response=response)

    def _get(url: str, **_: object):
        called_urls.append(url)
        if "://www." in url:
            return _RespForbidden()
        return _RespOk()

    monkeypatch.setattr("apps.api.app.services.tavily_discovery.time.sleep", lambda *_: None)
    monkeypatch.setattr("apps.api.app.services.tavily_discovery.httpx.get", _get)

    candidate = TavilyCandidate(
        title="Reports", url="https://www.example.com/report.pdf", score=0.8
    )
    downloaded = download_discovery_candidate(
        candidate=candidate,
        timeout_seconds=5.0,
        max_document_bytes=1024 * 1024,
    )

    assert downloaded.filename == "report.pdf"
    assert "https://www.example.com/report.pdf" in called_urls
    assert "https://example.com/report.pdf" in called_urls
