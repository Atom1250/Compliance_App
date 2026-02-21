from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.core.config import Settings
from apps.api.app.services.regulatory_research.factory import build_regulatory_research_service
from apps.api.app.services.regulatory_research.types import ResearchRequest


def _prepare_db(tmp_path: Path) -> str:
    db_path = tmp_path / "research_factory.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    return db_url


def test_factory_uses_stub_provider_when_notebook_flag_off(tmp_path: Path) -> None:
    db_url = _prepare_db(tmp_path)
    engine = create_engine(db_url)
    settings = Settings(
        feature_reg_research_enabled=True,
        feature_notebooklm_enabled=False,
    )
    service = build_regulatory_research_service(settings)
    request = ResearchRequest(
        question="Map CSRD requirements",
        corpus_key="EU-CSRD-ESRS",
        mode="mapping",
    )
    with Session(engine) as session:
        response = service.query(session, req=request)
    assert response.provider == "stub"
    assert len(response.citations) >= 1
