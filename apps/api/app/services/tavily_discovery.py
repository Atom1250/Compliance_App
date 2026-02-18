"""Tavily-backed web discovery for ESG reporting documents."""

from __future__ import annotations

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


def _build_query(company_name: str, reporting_year: int | None) -> str:
    year = str(reporting_year) if reporting_year is not None else "latest"
    return (
        f"{company_name} sustainability report {year} pdf "
        "esg annual report non-financial statement"
    )


def search_tavily_documents(
    *,
    company_name: str,
    reporting_year: int | None,
    api_key: str,
    base_url: str,
    timeout_seconds: float,
    max_results: int,
) -> list[TavilyCandidate]:
    query = _build_query(company_name, reporting_year)
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
    candidates: list[TavilyCandidate] = []
    for item in raw_results:
        url = str(item.get("url", "")).strip()
        if not url.startswith(("http://", "https://")):
            continue
        parsed = urlparse(url)
        if not parsed.path.lower().endswith(".pdf"):
            continue
        candidates.append(
            TavilyCandidate(
                title=str(item.get("title", "")).strip() or "Discovered ESG Document",
                url=url,
                score=float(item.get("score", 0.0)),
            )
        )
    return sorted(candidates, key=lambda item: (-item.score, item.url))


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
    response = httpx.get(candidate.url, timeout=timeout_seconds, follow_redirects=True)
    response.raise_for_status()
    content = response.content
    content_type = response.headers.get("content-type", "").lower()
    looks_like_pdf = content.startswith(b"%PDF-")
    if "application/pdf" not in content_type and not looks_like_pdf:
        raise ValueError("downloaded content is not a PDF")
    if not content:
        raise ValueError("empty downloaded document")
    if len(content) > max_document_bytes:
        raise ValueError("downloaded document exceeded size limit")
    return DownloadedDocument(
        content=content,
        filename=_filename_from_url(str(response.url)),
        title=candidate.title,
        source_url=candidate.url,
    )
