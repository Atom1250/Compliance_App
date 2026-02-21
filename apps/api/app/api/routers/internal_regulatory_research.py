"""Internal-only regulatory research workflow endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.app.core.auth import AuthContext, require_auth_context
from apps.api.app.core.config import get_settings
from apps.api.app.db.session import get_db_session
from apps.api.app.services.regulatory_research.factory import build_regulatory_research_service
from apps.api.app.services.regulatory_research.service import ResearchActor
from apps.api.app.services.regulatory_research.types import (
    ResearchRequest,
    ResearchResponse,
)

router = APIRouter(prefix="/internal/regulatory-research", tags=["internal-regulatory-research"])


class CitationResponse(BaseModel):
    source_title: str
    source_id: str | None = None
    locator: str | None = None
    quote: str | None = None
    url: str | None = None


class ResearchQueryBody(BaseModel):
    question: str = Field(min_length=1)
    corpus_key: str = Field(min_length=1)
    mode: str = Field(pattern="^(tagging|mapping|qa|draft_prd)$")
    requirement_id: str | None = None
    tags: list[str] = Field(default_factory=list)


class RequirementResearchQueryBody(BaseModel):
    question: str = Field(min_length=1)
    corpus_key: str = Field(min_length=1)
    mode: str = Field(pattern="^(tagging|mapping|qa|draft_prd)$")
    tags: list[str] = Field(default_factory=list)


class ResearchQueryResponse(BaseModel):
    answer_markdown: str
    citations: list[CitationResponse]
    provider: str
    request_hash: str
    latency_ms: int
    persisted_note_id: int | None = None


def _ensure_enabled() -> None:
    settings = get_settings()
    if not settings.feature_reg_research_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="regulatory research feature disabled",
        )


def _to_request(
    *,
    question: str,
    corpus_key: str,
    mode: str,
    requirement_id: str | None,
    tags: list[str],
) -> ResearchRequest:
    return ResearchRequest(
        question=question,
        corpus_key=corpus_key,
        mode=mode,  # type: ignore[arg-type]
        requirement_id=requirement_id,
        tags=tags,
    )


def _to_response(
    resp: ResearchResponse,
    *,
    persisted_note_id: int | None = None,
) -> ResearchQueryResponse:
    return ResearchQueryResponse(
        answer_markdown=resp.answer_markdown,
        citations=[CitationResponse(**citation.__dict__) for citation in resp.citations],
        provider=resp.provider,
        request_hash=resp.request_hash,
        latency_ms=resp.latency_ms,
        persisted_note_id=persisted_note_id,
    )


@router.post("/query", response_model=ResearchQueryResponse)
def query_research(
    body: ResearchQueryBody,
    auth: AuthContext = Depends(require_auth_context),
    actor_id: str | None = Header(default=None, alias="X-Actor-ID"),
    db: Session = Depends(get_db_session),
) -> ResearchQueryResponse:
    _ensure_enabled()
    settings = get_settings()
    service = build_regulatory_research_service(settings)
    req = _to_request(
        question=body.question,
        corpus_key=body.corpus_key,
        mode=body.mode,
        requirement_id=body.requirement_id,
        tags=body.tags,
    )
    actor = ResearchActor(id=actor_id or f"{auth.tenant_id}:api")

    if settings.feature_notebooklm_persist_results and body.requirement_id:
        note = service.query_and_maybe_persist_with_note(
            db,
            req=req,
            actor=actor,
        )
        return _to_response(note.response, persisted_note_id=note.note_id)

    response = service.query(db, req=req)
    return _to_response(response)


@router.post("/requirements/{requirement_id}/query", response_model=ResearchQueryResponse)
def query_requirement_research(
    requirement_id: str,
    body: RequirementResearchQueryBody,
    auth: AuthContext = Depends(require_auth_context),
    actor_id: str | None = Header(default=None, alias="X-Actor-ID"),
    db: Session = Depends(get_db_session),
) -> ResearchQueryResponse:
    _ensure_enabled()
    settings = get_settings()
    service = build_regulatory_research_service(settings)
    req = _to_request(
        question=body.question,
        corpus_key=body.corpus_key,
        mode=body.mode,
        requirement_id=requirement_id,
        tags=body.tags,
    )
    actor = ResearchActor(id=actor_id or f"{auth.tenant_id}:api")

    note = service.query_and_maybe_persist_with_note(
        db,
        req=req,
        actor=actor,
    )
    return _to_response(note.response, persisted_note_id=note.note_id)
