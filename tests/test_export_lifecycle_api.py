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


def _prepare_fixture(
    tmp_path: Path,
    *,
    run_status: str,
    include_assessment: bool,
    include_manifest: bool,
) -> tuple[str, int]:
    db_path = tmp_path / "export_lifecycle.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    with Session(engine) as session:
        company = Company(name="Export Lifecycle Co", tenant_id="default")
        session.add(company)
        session.flush()

        run = Run(company_id=company.id, tenant_id="default", status=run_status)
        session.add(run)
        session.flush()

        if include_assessment:
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

        if include_manifest:
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


def test_export_readiness_reports_blockers(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id = _prepare_fixture(
        tmp_path,
        run_status="queued",
        include_assessment=False,
        include_manifest=False,
    )
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    response = client.get(f"/runs/{run_id}/export-readiness", headers=AUTH_DEFAULT)
    assert response.status_code == 200
    payload = response.json()
    assert payload["report_ready"] is False
    assert payload["evidence_pack_ready"] is False
    assert payload["checks"] == {
        "run_completed": False,
        "has_manifest": False,
        "has_assessments": False,
    }
    assert payload["blocking_reasons"] == [
        "assessments_missing",
        "manifest_missing_for_report",
        "run_not_completed:queued",
    ]


def test_report_endpoint_returns_409_when_manifest_missing(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id = _prepare_fixture(
        tmp_path,
        run_status="completed",
        include_assessment=True,
        include_manifest=False,
    )
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    response = client.get(f"/runs/{run_id}/report", headers=AUTH_DEFAULT)
    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "report_not_ready",
        "reasons": ["manifest_missing_for_report"],
    }


def test_evidence_pack_endpoint_returns_409_when_assessments_missing(
    monkeypatch, tmp_path: Path
) -> None:
    db_url, run_id = _prepare_fixture(
        tmp_path,
        run_status="completed",
        include_assessment=False,
        include_manifest=True,
    )
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    monkeypatch.setenv("COMPLIANCE_APP_EVIDENCE_PACK_OUTPUT_ROOT", str(tmp_path / "packs"))
    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    response = client.get(f"/runs/{run_id}/evidence-pack", headers=AUTH_DEFAULT)
    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "evidence_pack_not_ready",
        "reasons": ["assessments_missing"],
    }


def test_export_readiness_is_tenant_scoped(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id = _prepare_fixture(
        tmp_path,
        run_status="completed",
        include_assessment=True,
        include_manifest=True,
    )
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    response = client.get(f"/runs/{run_id}/export-readiness", headers=AUTH_OTHER)
    assert response.status_code == 404
