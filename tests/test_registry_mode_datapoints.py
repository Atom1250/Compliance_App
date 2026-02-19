from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.core.config import get_settings
from apps.api.app.db.models import Company, Run
from apps.api.app.services.assessment_pipeline import (
    AssessmentRunConfig,
    execute_assessment_pipeline,
)
from apps.api.app.services.llm_extraction import ExtractionClient
from apps.api.app.services.regulatory_registry import sync_from_filesystem


class _AbsentTransport:
    def create_response(self, **kwargs):
        del kwargs
        return {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": (
                                '{"status":"Absent","value":null,"evidence_chunk_ids":[],"rationale":"ok"}'
                            ),
                        }
                    ],
                }
            ]
        }


def _prepare_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "registry_mode_datapoints.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    return Session(engine, expire_on_commit=False)


def test_registry_mode_generates_datapoints_when_flag_enabled(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_FEATURE_REGISTRY_COMPILER", "true")
    get_settings.cache_clear()

    with _prepare_session(tmp_path) as session:
        sync_from_filesystem(session, bundles_root=Path("app/regulatory/bundles"))
        company = Company(name="Registry Co", reporting_year=2026)
        session.add(company)
        session.commit()

        run = Run(company_id=company.id, status="running", compiler_mode="registry")
        session.add(run)
        session.commit()

        client = ExtractionClient(transport=_AbsentTransport(), model="deterministic-local-v1")
        assessments = execute_assessment_pipeline(
            session,
            extraction_client=client,
            config=AssessmentRunConfig(
                run_id=run.id,
                bundle_id="eu_csrd_sample",
                bundle_version="2026.01",
            ),
        )

    assert [item.datapoint_key for item in assessments] == ["ESRS-E1-1::E1-1-narrative"]


def test_registry_mode_flag_off_preserves_legacy_path(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_FEATURE_REGISTRY_COMPILER", "false")
    get_settings.cache_clear()

    with _prepare_session(tmp_path) as session:
        company = Company(name="Legacy Path Co", reporting_year=2026)
        session.add(company)
        session.commit()
        run = Run(company_id=company.id, status="running", compiler_mode="registry")
        session.add(run)
        session.commit()

        client = ExtractionClient(transport=_AbsentTransport(), model="deterministic-local-v1")
        with pytest.raises(ValueError, match="Bundle not found: eu_csrd_sample@2026.01"):
            execute_assessment_pipeline(
                session,
                extraction_client=client,
                config=AssessmentRunConfig(
                    run_id=run.id,
                    bundle_id="eu_csrd_sample",
                    bundle_version="2026.01",
                ),
            )
