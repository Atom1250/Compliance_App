from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.core.config import Settings
from apps.api.app.db.models import Company, RegulatoryRequirementResearchNote, Run
from apps.api.app.services.regulatory_research.provider import ResearchProvider
from apps.api.app.services.regulatory_research.service import (
    RegulatoryResearchService,
    ResearchActor,
)
from apps.api.app.services.regulatory_research.types import (
    Citation,
    ResearchRequest,
    ResearchResponse,
)


class _FakeProvider(ResearchProvider):
    def __init__(self, response: ResearchResponse):
        self.response = response
        self.calls = 0

    def query(self, req: ResearchRequest) -> ResearchResponse:
        self.calls += 1
        return self.response


def _db_url(tmp_path: Path) -> str:
    db_path = tmp_path / "research.sqlite"
    return f"sqlite:///{db_path}"


def _prepare_db(url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")


def _base_response() -> ResearchResponse:
    return ResearchResponse(
        answer_markdown="mapped",
        citations=[Citation(source_title="ESRS", locator="E1-1")],
        provider="notebooklm",
        confidence=0.7,
        latency_ms=10,
        request_hash="x" * 64,
    )


def test_service_returns_stub_when_master_flag_disabled(tmp_path: Path) -> None:
    url = _db_url(tmp_path)
    _prepare_db(url)
    provider = _FakeProvider(_base_response())
    settings = Settings(
        feature_reg_research_enabled=False,
        feature_notebooklm_enabled=True,
    )
    service = RegulatoryResearchService(provider=provider, settings=settings)

    req = ResearchRequest(question="Q", corpus_key="eu", mode="qa")
    engine = create_engine(url)
    with Session(engine) as session:
        resp = service.query(session, req=req)

    assert resp.provider == "stub"
    assert "disabled" in resp.answer_markdown.lower()
    assert provider.calls == 0


def test_service_returns_stub_when_provider_flag_disabled(tmp_path: Path) -> None:
    url = _db_url(tmp_path)
    _prepare_db(url)
    provider = _FakeProvider(_base_response())
    settings = Settings(feature_reg_research_enabled=True, feature_notebooklm_enabled=False)
    service = RegulatoryResearchService(provider=provider, settings=settings)

    req = ResearchRequest(question="Q", corpus_key="eu", mode="qa")
    engine = create_engine(url)
    with Session(engine) as session:
        resp = service.query(session, req=req)

    assert resp.provider == "stub"
    assert provider.calls == 0


def test_service_calls_provider_and_caches_response(tmp_path: Path) -> None:
    url = _db_url(tmp_path)
    _prepare_db(url)
    provider = _FakeProvider(_base_response())
    settings = Settings(feature_reg_research_enabled=True, feature_notebooklm_enabled=True)
    service = RegulatoryResearchService(provider=provider, settings=settings)

    req = ResearchRequest(question="Q", corpus_key="eu", mode="qa")
    engine = create_engine(url)
    with Session(engine) as session:
        first = service.query(session, req=req)
        second = service.query(session, req=req)

    assert first.provider == "notebooklm"
    assert second.provider == "notebooklm"
    assert provider.calls == 1


def test_service_strict_mode_rejects_empty_citations(tmp_path: Path) -> None:
    url = _db_url(tmp_path)
    _prepare_db(url)
    provider = _FakeProvider(
        ResearchResponse(
            answer_markdown="mapped",
            citations=[],
            provider="notebooklm",
            confidence=0.2,
            latency_ms=10,
            request_hash="x" * 64,
        )
    )
    settings = Settings(
        feature_reg_research_enabled=True,
        feature_notebooklm_enabled=True,
        feature_notebooklm_strict_citations=True,
    )
    service = RegulatoryResearchService(provider=provider, settings=settings)

    req = ResearchRequest(question="Q", corpus_key="eu", mode="qa")
    engine = create_engine(url)
    with Session(engine) as session:
        with pytest.raises(ValueError):
            service.query(session, req=req)


def test_query_and_maybe_persist_respects_persist_flag(tmp_path: Path) -> None:
    url = _db_url(tmp_path)
    _prepare_db(url)
    provider = _FakeProvider(_base_response())
    settings = Settings(
        feature_reg_research_enabled=True,
        feature_notebooklm_enabled=True,
        feature_notebooklm_persist_results=True,
        feature_notebooklm_strict_citations=False,
    )
    service = RegulatoryResearchService(provider=provider, settings=settings)

    req = ResearchRequest(
        question="Q",
        corpus_key="eu",
        mode="mapping",
        requirement_id="REQ-1",
    )
    engine = create_engine(url)
    with Session(engine) as session:
        # seed minimal rows to mirror runtime DB usage footprint
        company = Company(name="Research Co")
        session.add(company)
        session.flush()
        session.add(Run(company_id=company.id, status="queued"))
        session.commit()
        service.query_and_maybe_persist(
            session,
            req=req,
            actor=ResearchActor(id="user@example.com"),
        )
        rows = session.scalars(
            select(RegulatoryRequirementResearchNote).where(
                RegulatoryRequirementResearchNote.requirement_id == "REQ-1"
            )
        ).all()

    assert len(rows) == 1
    assert rows[0].created_by == "user@example.com"


def test_scoring_modules_do_not_import_regulatory_research() -> None:
    scoring_files = [
        Path("apps/api/app/services/run_execution_worker.py"),
        Path("apps/api/app/services/assessment_pipeline.py"),
        Path("apps/api/app/services/verification.py"),
    ]
    for path in scoring_files:
        text = path.read_text()
        assert "regulatory_research" not in text
