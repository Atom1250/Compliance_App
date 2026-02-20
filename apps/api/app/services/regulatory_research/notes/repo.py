"""Repository for requirement-linked research notes."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.db.models import RegulatoryRequirementResearchNote
from apps.api.app.services.regulatory_research.types import Citation


def insert_note(
    db: Session,
    *,
    requirement_id: str,
    request_hash: str,
    provider: str,
    corpus_key: str,
    mode: str,
    question: str,
    answer_markdown: str,
    citations: list[Citation],
    created_by: str,
) -> RegulatoryRequirementResearchNote:
    note = RegulatoryRequirementResearchNote(
        requirement_id=requirement_id,
        request_hash=request_hash,
        provider=provider,
        corpus_key=corpus_key,
        mode=mode,
        question=question,
        answer_markdown=answer_markdown,
        citations_jsonb=[
            {
                "source_title": item.source_title,
                "source_id": item.source_id,
                "locator": item.locator,
                "quote": item.quote,
                "url": item.url,
            }
            for item in citations
        ],
        created_by=created_by,
    )
    db.add(note)
    db.flush()
    return note


def list_notes(db: Session, *, requirement_id: str) -> list[RegulatoryRequirementResearchNote]:
    return db.scalars(
        select(RegulatoryRequirementResearchNote)
        .where(RegulatoryRequirementResearchNote.requirement_id == requirement_id)
        .order_by(RegulatoryRequirementResearchNote.created_at.desc())
    ).all()
