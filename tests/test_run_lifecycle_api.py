from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import Company, DatapointAssessment, Run, RunManifest
from apps.api.main import app

AUTH_DEFAULT = {"X-API-Key": "dev-key", "X-Tenant-ID": "default"}
AUTH_OTHER = {"X-API-Key": "dev-key", "X-Tenant-ID": "other"}


def _prepare_fixture(tmp_path: Path) -> tuple[str, int]:
    db_path = tmp_path / "run_lifecycle.sqlite"
    db_url = f"sqlite:///{db_path}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    with Session(engine) as session:
        company = Company(name="Lifecycle Co", tenant_id="default")
        session.add(company)
        session.commit()
        return db_url, company.id


def test_run_lifecycle_endpoints_happy_path(monkeypatch, tmp_path: Path) -> None:
    db_url, company_id = _prepare_fixture(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    created = client.post("/runs", json={"company_id": company_id}, headers=AUTH_DEFAULT)
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    assert created.json()["status"] == "queued"

    status_response = client.get(f"/runs/{run_id}/status", headers=AUTH_DEFAULT)
    assert status_response.status_code == 200
    assert status_response.json() == {"run_id": run_id, "status": "queued"}

    report_response = client.get(f"/runs/{run_id}/report", headers=AUTH_DEFAULT)
    assert report_response.status_code == 409
    assert report_response.json()["detail"] == "report available only for completed runs"

    report_html_response = client.get(f"/runs/{run_id}/report-html", headers=AUTH_DEFAULT)
    assert report_html_response.status_code == 409
    assert report_html_response.json()["detail"] == "report available only for completed runs"



def test_run_lifecycle_endpoints_are_tenant_scoped(monkeypatch, tmp_path: Path) -> None:
    db_url, company_id = _prepare_fixture(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    created = client.post("/runs", json={"company_id": company_id}, headers=AUTH_DEFAULT)
    assert created.status_code == 200
    run_id = created.json()["run_id"]

    forbidden_status = client.get(f"/runs/{run_id}/status", headers=AUTH_OTHER)
    assert forbidden_status.status_code == 404

    forbidden_report = client.get(f"/runs/{run_id}/report", headers=AUTH_OTHER)
    assert forbidden_report.status_code == 404

    forbidden_report_html = client.get(f"/runs/{run_id}/report-html", headers=AUTH_OTHER)
    assert forbidden_report_html.status_code == 404



def test_run_lifecycle_events_are_recorded(monkeypatch, tmp_path: Path) -> None:
    db_url, company_id = _prepare_fixture(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    created = client.post("/runs", json={"company_id": company_id}, headers=AUTH_DEFAULT)
    run_id = created.json()["run_id"]

    client.get(f"/runs/{run_id}/status", headers=AUTH_DEFAULT)
    engine = create_engine(db_url)
    with Session(engine) as session:
        run = session.scalar(select(Run).where(Run.id == run_id))
        assert run is not None
        run.status = "completed"
        session.add(
            DatapointAssessment(
                run_id=run.id,
                tenant_id="default",
                datapoint_key="ESRS-E1-1",
                status="Absent",
                value=None,
                evidence_chunk_ids="[]",
                rationale="No evidence.",
                model_name="deterministic-local-v1",
                prompt_hash="a" * 64,
                retrieval_params='{"query_mode":"hybrid","top_k":5}',
            )
        )
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

    report_response = client.get(f"/runs/{run_id}/report", headers=AUTH_DEFAULT)
    assert report_response.status_code == 200

    events = client.get(f"/runs/{run_id}/events", headers=AUTH_DEFAULT)
    assert events.status_code == 200
    event_types = [item["event_type"] for item in events.json()["events"]]
    assert event_types == ["run.created", "run.status.requested", "run.report.requested"]
