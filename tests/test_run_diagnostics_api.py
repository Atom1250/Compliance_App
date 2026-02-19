import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.requirements.importer import import_bundle, load_bundle
from apps.api.app.db.models import Company, DatapointAssessment, Run, RunEvent, RunManifest
from apps.api.main import app

AUTH_DEFAULT = {"X-API-Key": "dev-key", "X-Tenant-ID": "default"}
AUTH_OTHER = {"X-API-Key": "dev-key", "X-Tenant-ID": "other"}


def _prepare_fixture(tmp_path: Path) -> tuple[str, int, int]:
    db_path = tmp_path / "run_diagnostics.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)

    with Session(engine) as session:
        import_bundle(session, load_bundle(Path("requirements/esrs_mini/bundle.json")))
        company = Company(
            name="Diagnostics Co",
            tenant_id="default",
            employees=300,
            turnover=12_000_000.0,
            listed_status=True,
            reporting_year=2026,
        )
        session.add(company)
        session.flush()
        completed_run = Run(
            company_id=company.id,
            tenant_id="default",
            status="completed",
            compiler_mode="legacy",
        )
        session.add(completed_run)
        session.flush()
        failed_run = Run(
            company_id=company.id,
            tenant_id="default",
            status="failed",
            compiler_mode="legacy",
        )
        session.add(failed_run)
        session.flush()

        session.add(
            RunManifest(
                run_id=completed_run.id,
                tenant_id="default",
                document_hashes='["a"]',
                bundle_id="esrs_mini",
                bundle_version="2026.01",
                retrieval_params='{"query_mode":"hybrid"}',
                model_name="deterministic-local-v1",
                prompt_hash="p" * 64,
                git_sha="g" * 40,
            )
        )
        session.add_all(
            [
                DatapointAssessment(
                    run_id=completed_run.id,
                    tenant_id="default",
                    datapoint_key="ESRS-E1-1",
                    status="Present",
                    value="value",
                    evidence_chunk_ids='["chunk-1","chunk-2"]',
                    rationale="ok",
                    model_name="deterministic-local-v1",
                    prompt_hash="p" * 64,
                    retrieval_params='{"query_mode":"hybrid"}',
                ),
                DatapointAssessment(
                    run_id=completed_run.id,
                    tenant_id="default",
                    datapoint_key="ESRS-E1-6",
                    status="Partial",
                    value="value",
                    evidence_chunk_ids='["chunk-2","chunk-3"]',
                    rationale="ok",
                    model_name="deterministic-local-v1",
                    prompt_hash="p" * 64,
                    retrieval_params='{"query_mode":"hybrid"}',
                ),
            ]
        )
        session.add_all(
            [
                RunEvent(
                    run_id=completed_run.id,
                    tenant_id="default",
                    event_type="run.created",
                    payload="{}",
                ),
                RunEvent(
                    run_id=completed_run.id,
                    tenant_id="default",
                    event_type="run.execution.queued",
                    payload="{}",
                ),
                RunEvent(
                    run_id=completed_run.id,
                    tenant_id="default",
                    event_type="run.execution.started",
                    payload="{}",
                ),
                RunEvent(
                    run_id=completed_run.id,
                    tenant_id="default",
                    event_type="assessment.pipeline.started",
                    payload="{}",
                ),
                RunEvent(
                    run_id=completed_run.id,
                    tenant_id="default",
                    event_type="assessment.pipeline.completed",
                    payload="{}",
                ),
                RunEvent(
                    run_id=completed_run.id,
                    tenant_id="default",
                    event_type="run.execution.completed",
                    payload="{}",
                ),
                RunEvent(
                    run_id=failed_run.id,
                    tenant_id="default",
                    event_type="run.created",
                    payload="{}",
                ),
                RunEvent(
                    run_id=failed_run.id,
                    tenant_id="default",
                    event_type="run.execution.failed",
                    payload=json.dumps({"error": "provider timeout"}),
                ),
            ]
        )
        session.commit()
        return db_url, completed_run.id, failed_run.id


def test_run_diagnostics_returns_deterministic_metrics(monkeypatch, tmp_path: Path) -> None:
    db_url, completed_run_id, _ = _prepare_fixture(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    response = client.get(f"/runs/{completed_run_id}/diagnostics", headers=AUTH_DEFAULT)
    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == completed_run_id
    assert payload["status"] == "completed"
    assert payload["manifest_present"] is True
    assert payload["required_datapoints_count"] == 2
    assert payload["required_datapoints_error"] is None
    assert payload["assessment_count"] == 2
    assert payload["assessment_status_counts"] == {
        "Present": 1,
        "Partial": 1,
        "Absent": 0,
        "NA": 0,
    }
    assert payload["retrieval_hit_count"] == 3
    assert payload["latest_failure_reason"] is None
    assert payload["stage_outcomes"] == {
        "run.created": True,
        "run.execution.queued": True,
        "run.execution.started": True,
        "assessment.pipeline.started": True,
        "assessment.pipeline.completed": True,
        "run.execution.completed": True,
        "run.execution.failed": False,
    }
    assert payload["stage_event_counts"]["run.execution.completed"] == 1


def test_run_diagnostics_exposes_latest_failure_reason(monkeypatch, tmp_path: Path) -> None:
    db_url, _, failed_run_id = _prepare_fixture(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    response = client.get(f"/runs/{failed_run_id}/diagnostics", headers=AUTH_DEFAULT)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["manifest_present"] is False
    assert payload["required_datapoints_count"] is None
    assert payload["latest_failure_reason"] == "provider timeout"
    assert payload["stage_outcomes"]["run.execution.failed"] is True


def test_run_diagnostics_is_tenant_scoped(monkeypatch, tmp_path: Path) -> None:
    db_url, completed_run_id, _ = _prepare_fixture(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    forbidden = client.get(f"/runs/{completed_run_id}/diagnostics", headers=AUTH_OTHER)
    assert forbidden.status_code == 404
