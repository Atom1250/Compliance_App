from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.requirements.importer import import_bundle, load_bundle
from apps.api.app.db.models import Chunk, Company, DatapointAssessment, Document, Run
from apps.api.app.services.llm_extraction import ExtractionClient
from apps.api.main import app

AUTH_DEFAULT = {"X-API-Key": "dev-key", "X-Tenant-ID": "default"}
AUTH_OTHER = {"X-API-Key": "dev-key", "X-Tenant-ID": "other"}


def _prepare_fixture(tmp_path: Path) -> tuple[str, int]:
    db_path = tmp_path / "run_execute.sqlite"
    db_url = f"sqlite:///{db_path}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    with Session(engine, expire_on_commit=False) as session:
        import_bundle(session, load_bundle(Path("requirements/esrs_mini/bundle.json")))

        company = Company(
            name="Execute Co",
            tenant_id="default",
            employees=300,
            turnover=12_000_000.0,
            listed_status=True,
            reporting_year=2026,
        )
        session.add(company)
        session.flush()

        run = Run(company_id=company.id, tenant_id="default", status="queued")
        session.add(run)
        session.flush()

        document = Document(company_id=company.id, tenant_id="default", title="Report")
        session.add(document)
        session.flush()

        session.add(
            Chunk(
                document_id=document.id,
                chunk_id="exec-chunk-1",
                page_number=1,
                start_offset=0,
                end_offset=64,
                text="Transition plan and gross emissions are discussed.",
                content_tsv="transition plan gross emissions",
            )
        )
        session.commit()
        return db_url, run.id


def test_run_execute_happy_path_stores_assessments(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id = _prepare_fixture(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    response = client.post(
        f"/runs/{run_id}/execute",
        json={"bundle_id": "esrs_mini", "bundle_version": "2026.01"},
        headers=AUTH_DEFAULT,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == run_id
    assert payload["status"] == "completed"
    assert payload["assessment_count"] == 2

    status_response = client.get(f"/runs/{run_id}/status", headers=AUTH_DEFAULT)
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"

    events = client.get(f"/runs/{run_id}/events", headers=AUTH_DEFAULT)
    assert events.status_code == 200
    event_types = [item["event_type"] for item in events.json()["events"]]
    assert "run.execution.started" in event_types
    assert "run.execution.completed" in event_types

    engine = create_engine(db_url)
    with Session(engine) as session:
        stored = session.scalars(
            select(DatapointAssessment).where(DatapointAssessment.run_id == run_id)
        ).all()
    assert len(stored) == 2


def test_run_execute_is_tenant_scoped(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id = _prepare_fixture(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    response = client.post(
        f"/runs/{run_id}/execute",
        json={"bundle_id": "esrs_mini", "bundle_version": "2026.01"},
        headers=AUTH_OTHER,
    )
    assert response.status_code == 404


def test_run_execute_accepts_local_lm_studio_provider(monkeypatch, tmp_path: Path) -> None:
    class _MockTransport:
        def create_response(self, *, model, input_text, temperature, json_schema):
            del model, input_text, temperature, json_schema
            return {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": (
                                    '{"status":"Absent","value":null,"evidence_chunk_ids":[],'  # noqa: E501
                                    '"rationale":"Mock LM Studio provider path."}'
                                ),
                            }
                        ],
                    }
                ]
            }

    db_url, run_id = _prepare_fixture(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    from apps.api.app.api.routers import materiality as materiality_router_module
    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr(
        materiality_router_module,
        "build_extraction_client_from_settings",
        lambda _settings: ExtractionClient(
            transport=_MockTransport(),
            model="ministral-3-8b-instruct-2512-mlx",
        ),
    )

    client = TestClient(app)
    response = client.post(
        f"/runs/{run_id}/execute",
        json={
            "bundle_id": "esrs_mini",
            "bundle_version": "2026.01",
            "llm_provider": "local_lm_studio",
        },
        headers=AUTH_DEFAULT,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
