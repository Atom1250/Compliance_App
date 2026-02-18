from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.requirements.importer import import_bundle, load_bundle
from apps.api.app.db.models import (
    Chunk,
    Company,
    DatapointAssessment,
    Document,
    DocumentFile,
    Run,
    RunCacheEntry,
)
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
            DocumentFile(
                document_id=document.id,
                sha256_hash="a" * 64,
                storage_uri="file://object-store/default/a.pdf",
            )
        )

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


def test_run_execute_persists_and_returns_manifest(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id = _prepare_fixture(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    monkeypatch.setenv("COMPLIANCE_APP_GIT_SHA", "deadbeef" * 5)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    execute_response = client.post(
        f"/runs/{run_id}/execute",
        json={
            "bundle_id": "esrs_mini",
            "bundle_version": "2026.01",
            "retrieval_top_k": 7,
            "retrieval_model_name": "default",
        },
        headers=AUTH_DEFAULT,
    )
    assert execute_response.status_code == 200

    manifest_response = client.get(f"/runs/{run_id}/manifest", headers=AUTH_DEFAULT)
    assert manifest_response.status_code == 200
    payload = manifest_response.json()
    assert payload["run_id"] == run_id
    assert payload["document_hashes"] == ["a" * 64]
    assert payload["bundle_id"] == "esrs_mini"
    assert payload["bundle_version"] == "2026.01"
    assert payload["retrieval_params"] == {
        "bundle_id": "esrs_mini",
        "bundle_version": "2026.01",
        "llm_provider": "deterministic_fallback",
        "query_mode": "hybrid",
        "retrieval_model_name": "default",
        "top_k": 7,
    }
    assert payload["model_name"] == "deterministic-local-v1"
    assert len(payload["prompt_hash"]) == 64
    assert payload["git_sha"] == "deadbeef" * 5


def test_run_manifest_is_tenant_scoped(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id = _prepare_fixture(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    execute_response = client.post(
        f"/runs/{run_id}/execute",
        json={"bundle_id": "esrs_mini", "bundle_version": "2026.01"},
        headers=AUTH_DEFAULT,
    )
    assert execute_response.status_code == 200

    forbidden = client.get(f"/runs/{run_id}/manifest", headers=AUTH_OTHER)
    assert forbidden.status_code == 404


def test_run_execute_cache_hit_skips_pipeline_and_preserves_cached_output(
    monkeypatch, tmp_path: Path
) -> None:
    db_url, run_id = _prepare_fixture(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.api.routers import materiality as materiality_router_module
    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    call_count = {"count": 0}
    original_execute = materiality_router_module.execute_assessment_pipeline

    def counting_execute(*args, **kwargs):
        call_count["count"] += 1
        return original_execute(*args, **kwargs)

    monkeypatch.setattr(materiality_router_module, "execute_assessment_pipeline", counting_execute)
    client = TestClient(app)

    payload = {
        "bundle_id": "esrs_mini",
        "bundle_version": "2026.01",
        "retrieval_top_k": 5,
        "retrieval_model_name": "default",
        "llm_provider": "deterministic_fallback",
    }
    first = client.post(f"/runs/{run_id}/execute", json=payload, headers=AUTH_DEFAULT)
    assert first.status_code == 200

    engine = create_engine(db_url)
    with Session(engine) as session:
        first_entry = session.scalar(select(RunCacheEntry))
        assert first_entry is not None
        first_cached_output = first_entry.output_json
        assert len(first_cached_output) > 0

    second = client.post(f"/runs/{run_id}/execute", json=payload, headers=AUTH_DEFAULT)
    assert second.status_code == 200
    assert first.json() == second.json()
    assert call_count["count"] == 1

    with Session(engine) as session:
        entries = session.scalars(select(RunCacheEntry)).all()
        assert len(entries) == 1
        assert entries[0].output_json == first_cached_output
