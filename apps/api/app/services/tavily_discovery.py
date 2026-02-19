"""Tavily-backed web discovery for ESG reporting documents."""

from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True)
class TavilyCandidate:
    title: str
    url: str
    score: float


@dataclass(frozen=True)
class DownloadedDocument:
    content: bytes
    filename: str
    title: str
    source_url: str


def is_pdf_candidate_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.path.lower().endswith(".pdf")


def _query_variants(company_name: str, year: int | None) -> list[str]:
    year_text = str(year) if year is not None else "latest"
    return [
        f"{company_name} sustainability report {year_text} pdf",
        f"{company_name} annual report {year_text} esg pdf",
        f"{company_name} non-financial statement {year_text} pdf",
    ]


def _reporting_years(start_year: int | None, end_year: int | None) -> list[int | None]:
    if start_year is None and end_year is None:
        return [None]
    if start_year is None:
        start_year = end_year
    if end_year is None:
        end_year = start_year
    assert start_year is not None
    assert end_year is not None
    if start_year > end_year:
        start_year, end_year = end_year, start_year
    return list(range(start_year, end_year + 1))


def search_tavily_documents(
    *,
    company_name: str,
    reporting_year: int | None,
    reporting_year_start: int | None,
    reporting_year_end: int | None,
    api_key: str,
    base_url: str,
    timeout_seconds: float,
    max_results: int,
) -> list[TavilyCandidate]:
    years = _reporting_years(reporting_year_start, reporting_year_end)
    if years == [None] and reporting_year is not None:
        years = [reporting_year]
    queries: list[str] = []
    for year in years:
        queries.extend(_query_variants(company_name, year))

    by_url: dict[str, TavilyCandidate] = {}
    for query in queries:
        response = httpx.post(
            base_url,
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": max_results,
                "include_raw_content": False,
            },
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        raw_results = payload.get("results", [])
        for item in raw_results:
            url = str(item.get("url", "")).strip()
            if not url.startswith(("http://", "https://")):
                continue
            title = str(item.get("title", "")).strip() or "Discovered ESG Document"
            score = float(item.get("score", 0.0))
            current = by_url.get(url)
            if current is None or score > current.score:
                by_url[url] = TavilyCandidate(title=title, url=url, score=score)
    return sorted(by_url.values(), key=lambda item: (-item.score, item.url, item.title))


def _filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    basename = parsed.path.rsplit("/", maxsplit=1)[-1].strip()
    return basename or "discovered-document.pdf"


def download_discovery_candidate(
    *,
    candidate: TavilyCandidate,
    timeout_seconds: float,
    max_document_bytes: int,
) -> DownloadedDocument:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept": "application/pdf,*/*;q=0.8",
    }
    last_exc: Exception | None = None
    response: httpx.Response | None = None
    for attempt in range(1, 4):
        try:
            response = httpx.get(
                candidate.url,
                timeout=timeout_seconds,
                follow_redirects=True,
                headers=headers,
            )
            response.raise_for_status()
            break
        except Exception as exc:  # pragma: no cover - network dependent
            last_exc = exc
            if attempt == 3:
                raise
            time.sleep(0.2 * attempt)
    if response is None:
        if last_exc is not None:
            raise last_exc
        raise ValueError("download failed")

    content_type = response.headers.get("content-type", "").lower()
    content_length = response.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > max_document_bytes:
                raise ValueError("downloaded document exceeded size limit")
        except ValueError:
            raise ValueError("downloaded document exceeded size limit")
    content = response.content
    if not content:
        raise ValueError("empty downloaded document")
    looks_like_pdf = content.startswith(b"%PDF-")
    if "application/pdf" not in content_type and not looks_like_pdf:
        raise ValueError("downloaded content is not a PDF")
    if len(content) > max_document_bytes:
        raise ValueError("downloaded document exceeded size limit")
    return DownloadedDocument(
        content=content,
        filename=_filename_from_url(str(response.url)),
        title=candidate.title,
        source_url=candidate.url,
    )
