from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import Company, DatapointAssessment, Run
from apps.api.main import app

AUTH_DEFAULT = {"X-API-Key": "dev-key", "X-Tenant-ID": "default"}


def _prepare_fixture(tmp_path: Path) -> tuple[str, int]:
    db_path = tmp_path / "registry_report_matrix.sqlite"
    db_url = f"sqlite:///{db_path}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    with Session(engine) as session:
        company = Company(name="Matrix Co", tenant_id="default")
        session.add(company)
        session.flush()
        run = Run(
            company_id=company.id,
            tenant_id="default",
            status="completed",
            compiler_mode="registry",
        )
        session.add(run)
        session.flush()
        session.add(
            DatapointAssessment(
                run_id=run.id,
                tenant_id="default",
                datapoint_key="OBL-1::ELEM-1",
                status="Present",
                value="yes",
                evidence_chunk_ids='["chunk-1"]',
                rationale="ok",
                model_name="deterministic-local-v1",
                prompt_hash="a" * 64,
                retrieval_params='{"query_mode":"hybrid","top_k":3}',
            )
        )
        session.commit()
        return db_url, run.id


def test_report_matrix_section_requires_feature_flag(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id = _prepare_fixture(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    monkeypatch.setenv("COMPLIANCE_APP_FEATURE_REGISTRY_REPORT_MATRIX", "false")

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    disabled = client.get(f"/runs/{run_id}/report-html", headers=AUTH_DEFAULT)
    assert disabled.status_code == 200
    assert 'id="registry-coverage-matrix"' not in disabled.text

    monkeypatch.setenv("COMPLIANCE_APP_FEATURE_REGISTRY_REPORT_MATRIX", "true")
    get_settings.cache_clear()
    enabled = client.get(f"/runs/{run_id}/report-html", headers=AUTH_DEFAULT)
    assert enabled.status_code == 200
    assert 'id="registry-coverage-matrix"' in enabled.text
    assert "<td>OBL-1</td>" in enabled.text
