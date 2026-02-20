"""Orchestrator for configurable regulatory research providers."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from sqlalchemy.orm import Session

from apps.api.app.core.config import Settings
from apps.api.app.services.regulatory_research.cache import repo as cache_repo
from apps.api.app.services.regulatory_research.citations.validator import validate_citations
from apps.api.app.services.regulatory_research.hash import compute_request_hash
from apps.api.app.services.regulatory_research.notes import repo as notes_repo
from apps.api.app.services.regulatory_research.provider import ResearchProvider
from apps.api.app.services.regulatory_research.types import ResearchRequest, ResearchResponse


@dataclass(frozen=True)
class ResearchActor:
    id: str


class RegulatoryResearchService:
    def __init__(
        self,
        *,
        provider: ResearchProvider,
        settings: Settings,
        provider_name: str = "notebooklm",
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._provider_name = provider_name

    def _strict_citations_enabled(self) -> bool:
        explicit = self._settings.feature_notebooklm_strict_citations
        if explicit is not None:
            return explicit
        return self._settings.runtime_environment.lower() == "staging"

    def _disabled_response(self, *, req: ResearchRequest, message: str) -> ResearchResponse:
        return ResearchResponse(
            answer_markdown=message,
            citations=[],
            provider="stub",
            confidence=None,
            latency_ms=0,
            request_hash=compute_request_hash(req),
            can_persist=False,
        )

    def query(self, db: Session, *, req: ResearchRequest) -> ResearchResponse:
        request_hash = compute_request_hash(req)
        if not self._settings.feature_reg_research_enabled:
            return self._disabled_response(
                req=req,
                message="Regulatory research disabled by feature flag.",
            )
        if not self._settings.feature_notebooklm_enabled:
            return self._disabled_response(
                req=req,
                message="NotebookLM provider disabled by feature flag.",
            )

        cached = cache_repo.get_cached_response(db, request_hash=request_hash)
        if cached is not None:
            return cached

        started = monotonic()
        try:
            provider_resp = self._provider.query(req)
            elapsed = int((monotonic() - started) * 1000)
            validated = validate_citations(
                provider_resp,
                strict=self._strict_citations_enabled(),
            )
            response = ResearchResponse(
                answer_markdown=provider_resp.answer_markdown,
                citations=provider_resp.citations,
                provider=provider_resp.provider,
                confidence=provider_resp.confidence,
                latency_ms=elapsed,
                request_hash=request_hash,
                can_persist=validated.can_persist,
            )
            cache_repo.set_success(
                db,
                request_hash=request_hash,
                provider=response.provider,
                corpus_key=req.corpus_key,
                mode=req.mode,
                question=req.question,
                answer_markdown=response.answer_markdown,
                citations=response.citations,
                ttl_days=self._settings.notebooklm_cache_ttl_days,
            )
            db.commit()
            return response
        except Exception as exc:
            cache_repo.set_failure(
                db,
                request_hash=request_hash,
                provider=self._provider_name,
                corpus_key=req.corpus_key,
                mode=req.mode,
                question=req.question,
                error_message=str(exc),
                ttl_minutes=self._settings.notebooklm_cache_failure_ttl_minutes,
            )
            db.commit()
            raise

    def query_and_maybe_persist(
        self,
        db: Session,
        *,
        req: ResearchRequest,
        actor: ResearchActor,
    ) -> ResearchResponse:
        response = self.query(db, req=req)
        if not self._settings.feature_notebooklm_persist_results:
            return response
        if req.requirement_id is None:
            raise ValueError("requirement_id is required when persistence is enabled")
        if not response.can_persist:
            raise ValueError("Cannot persist research response without valid citations")
        notes_repo.insert_note(
            db,
            requirement_id=req.requirement_id,
            request_hash=response.request_hash,
            provider=response.provider,
            corpus_key=req.corpus_key,
            mode=req.mode,
            question=req.question,
            answer_markdown=response.answer_markdown,
            citations=response.citations,
            created_by=actor.id,
        )
        db.commit()
        return response
