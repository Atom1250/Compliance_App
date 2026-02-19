from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import Company, DatapointAssessment, Run, RunManifest
from apps.api.main import app

AUTH_DEFAULT = {"X-API-Key": "dev-key", "X-Tenant-ID": "default"}
AUTH_OTHER = {"X-API-Key": "dev-key", "X-Tenant-ID": "other"}


def _prepare_fixture(tmp_path: Path, *, status: str = "completed") -> tuple[str, int]:
    db_path = tmp_path / "report_preview_api.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    with Session(engine) as session:
        company = Company(name="Preview Co", tenant_id="default")
        session.add(company)
        session.flush()

        run = Run(company_id=company.id, tenant_id="default", status=status)
        session.add(run)
        session.flush()

        assessments = [
            DatapointAssessment(
                run_id=run.id,
                datapoint_key="ESRS-E1-1",
                status="Present",
                value="value-a",
                evidence_chunk_ids='["chunk-b","chunk-a"]',
                rationale="Rationale A.",
                model_name="deterministic-local-v1",
                prompt_hash="a" * 64,
                retrieval_params='{"query_mode":"hybrid","top_k":5}',
            ),
            DatapointAssessment(
                run_id=run.id,
                datapoint_key="ESRS-E1-2",
                status="Partial",
                value=None,
                evidence_chunk_ids='["chunk-c"]',
                rationale="Rationale B.",
                model_name="deterministic-local-v1",
                prompt_hash="b" * 64,
                retrieval_params='{"query_mode":"hybrid","top_k":5}',
            ),
            DatapointAssessment(
                run_id=run.id,
                datapoint_key="ESRS-E1-3",
                status="Absent",
                value=None,
                evidence_chunk_ids="[]",
                rationale="Rationale C.",
                model_name="deterministic-local-v1",
                prompt_hash="c" * 64,
                retrieval_params='{"query_mode":"hybrid","top_k":5}',
            ),
            DatapointAssessment(
                run_id=run.id,
                datapoint_key="ESRS-E1-4",
                status="NA",
                value=None,
                evidence_chunk_ids="[]",
                rationale="Rationale D.",
                model_name="deterministic-local-v1",
                prompt_hash="d" * 64,
                retrieval_params='{"query_mode":"hybrid","top_k":5}',
            ),
        ]
        session.add_all(assessments)
        session.add(
            RunManifest(
                run_id=run.id,
                tenant_id="default",
                document_hashes="[]",
                bundle_id="esrs_mini",
                bundle_version="2026.01",
                retrieval_params='{"query_mode":"hybrid","top_k":5}',
                model_name="deterministic-local-v1",
                prompt_hash="a" * 64,
                git_sha="deadbeef",
            )
        )
        session.commit()
        return db_url, run.id


def test_report_preview_returns_html_and_structured_sections(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id = _prepare_fixture(tmp_path, status="completed")
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    response = client.get(f"/runs/{run_id}/report-preview", headers=AUTH_DEFAULT)
    assert response.status_code == 200
    payload = response.json()

    assert payload["run_id"] == run_id
    assert f"Compliance Report for Run {run_id}" in payload["html"]
    assert payload["summary"] == {
        "covered": 2,
        "denominator_datapoints": 3,
        "excluded_na_count": 1,
        "coverage_pct": 66.66666666666666,
    }
    assert payload["metrics"] == {
        "present": 1,
        "partial": 1,
        "absent": 1,
        "na": 1,
        "total_datapoints": 4,
    }
    assert payload["gaps"] == [
        {"datapoint_key": "ESRS-E1-2", "status": "Partial"},
        {"datapoint_key": "ESRS-E1-3", "status": "Absent"},
    ]
    assert payload["rows"][0] == {
        "datapoint_key": "ESRS-E1-1",
        "status": "Present",
        "value": "value-a",
        "citations": ["chunk-a", "chunk-b"],
        "rationale": "Rationale A.",
    }


def test_report_preview_is_tenant_scoped(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id = _prepare_fixture(tmp_path, status="completed")
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    response = client.get(f"/runs/{run_id}/report-preview", headers=AUTH_OTHER)
    assert response.status_code == 404


def test_report_preview_requires_completed_run(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id = _prepare_fixture(tmp_path, status="queued")
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    response = client.get(f"/runs/{run_id}/report-preview", headers=AUTH_DEFAULT)
    assert response.status_code == 409
    assert response.json()["detail"] == "report available only for completed runs"
