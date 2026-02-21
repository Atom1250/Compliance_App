"""Repository for regulatory research cache rows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.db.models import RegulatoryResearchCache
from apps.api.app.services.regulatory_research.types import Citation, ResearchResponse


@dataclass(frozen=True)
class RegulatoryResearchCacheRow:
    request_hash: str
    provider: str
    corpus_key: str
    mode: str
    question: str
    answer_markdown: str
    citations: list[Citation]
    status: str
    error_message: str | None
    created_at: datetime
    expires_at: datetime


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _to_response(row: RegulatoryResearchCache) -> ResearchResponse:
    citations_payload = row.citations_jsonb if isinstance(row.citations_jsonb, list) else []
    citations = [
        Citation(
            source_title=str(item.get("source_title", "")),
            source_id=item.get("source_id"),
            locator=item.get("locator"),
            quote=item.get("quote"),
            url=item.get("url"),
        )
        for item in citations_payload
        if isinstance(item, dict)
    ]
    return ResearchResponse(
        answer_markdown=row.answer_markdown,
        citations=citations,
        provider=row.provider,  # type: ignore[arg-type]
        latency_ms=0,
        request_hash=row.request_hash,
        confidence=None,
        can_persist=bool(citations),
    )


def get_cached_response(db: Session, *, request_hash: str) -> ResearchResponse | None:
    row = db.scalar(
        select(RegulatoryResearchCache).where(
            RegulatoryResearchCache.request_hash == request_hash,
        )
    )
    if row is None:
        return None
    if _as_utc(row.expires_at) < _utc_now():
        return None
    if row.status != "success":
        return None
    return _to_response(row)


def set_success(
    db: Session,
    *,
    request_hash: str,
    provider: str,
    corpus_key: str,
    mode: str,
    question: str,
    answer_markdown: str,
    citations: list[Citation],
    ttl_days: int,
) -> None:
    expiry = _utc_now() + timedelta(days=ttl_days)
    payload = [
        {
            "source_title": item.source_title,
            "source_id": item.source_id,
            "locator": item.locator,
            "quote": item.quote,
            "url": item.url,
        }
        for item in citations
    ]
    row = db.get(RegulatoryResearchCache, request_hash)
    if row is None:
        row = RegulatoryResearchCache(
            request_hash=request_hash,
            provider=provider,
            corpus_key=corpus_key,
            mode=mode,
            question=question,
            answer_markdown=answer_markdown,
            citations_jsonb=payload,
            status="success",
            error_message=None,
            expires_at=expiry,
        )
        db.add(row)
    else:
        row.provider = provider
        row.corpus_key = corpus_key
        row.mode = mode
        row.question = question
        row.answer_markdown = answer_markdown
        row.citations_jsonb = payload
        row.status = "success"
        row.error_message = None
        row.expires_at = expiry


def set_failure(
    db: Session,
    *,
    request_hash: str,
    provider: str,
    corpus_key: str,
    mode: str,
    question: str,
    error_message: str,
    ttl_minutes: int,
) -> None:
    expiry = _utc_now() + timedelta(minutes=ttl_minutes)
    row = db.get(RegulatoryResearchCache, request_hash)
    if row is None:
        row = RegulatoryResearchCache(
            request_hash=request_hash,
            provider=provider,
            corpus_key=corpus_key,
            mode=mode,
            question=question,
            answer_markdown="",
            citations_jsonb=[],
            status="failed",
            error_message=error_message,
            expires_at=expiry,
        )
        db.add(row)
    else:
        row.provider = provider
        row.corpus_key = corpus_key
        row.mode = mode
        row.question = question
        row.answer_markdown = ""
        row.citations_jsonb = []
        row.status = "failed"
        row.error_message = error_message
        row.expires_at = expiry
