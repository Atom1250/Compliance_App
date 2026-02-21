import time
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.requirements.importer import import_bundle, load_bundle
from apps.api.app.api.routers import documents as documents_router
from apps.api.app.db.models import Company, Run
from apps.api.app.services.tavily_discovery import DownloadedDocument, TavilyCandidate
from apps.api.main import app

AUTH_DEFAULT = {"X-API-Key": "dev-key", "X-Tenant-ID": "default"}


def _prepare_database(tmp_path: Path) -> tuple[str, int]:
    db_path = tmp_path / "guided_flow.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    with Session(engine) as session:
        import_bundle(session, load_bundle(Path("requirements/esrs_mini/bundle.json")))
        company = Company(
            name="Guided Flow Co",
            tenant_id="default",
            reporting_year=2026,
            listed_status=True,
        )
        session.add(company)
        session.commit()
        return db_url, company.id


def _wait_for_terminal_status(db_url: str, *, run_id: int, timeout_seconds: float = 4.0) -> str:
    engine = create_engine(db_url)
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        with Session(engine) as session:
            run = session.get(Run, run_id)
            assert run is not None
            if run.status in {"completed", "completed_with_warnings", "failed", "failed_pipeline"}:
                return run.status
        time.sleep(0.05)
    raise AssertionError("run did not reach terminal status in time")


def test_guided_flow_api_sequence_succeeds(monkeypatch, tmp_path: Path) -> None:
    db_url, company_id = _prepare_database(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    monkeypatch.setenv("COMPLIANCE_APP_OBJECT_STORAGE_ROOT", str(tmp_path / "object_store"))
    monkeypatch.setenv("COMPLIANCE_APP_TAVILY_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCE_APP_TAVILY_API_KEY", "test-key")

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()

    monkeypatch.setattr(
        documents_router,
        "search_tavily_documents",
        lambda **_: [
            TavilyCandidate(
                title="Guided Sustainability Report 2026",
                url="https://example.com/guided-report.pdf",
                score=0.9,
            )
        ],
    )
    monkeypatch.setattr(
        documents_router,
        "download_discovery_candidate",
        lambda **_: DownloadedDocument(
            content=b"%PDF-1.4 guided flow test bytes",
            filename="guided-report.pdf",
            title="Guided Sustainability Report 2026",
            source_url="https://example.com/guided-report.pdf",
        ),
    )

    client = TestClient(app)
    discovery = client.post(
        "/documents/auto-discover",
        json={"company_id": company_id, "max_documents": 1},
        headers=AUTH_DEFAULT,
    )
    assert discovery.status_code == 200
    assert discovery.json()["ingested_count"] == 1

    run_create = client.post("/runs", json={"company_id": company_id}, headers=AUTH_DEFAULT)
    assert run_create.status_code == 200
    run_id = run_create.json()["run_id"]

    execute = client.post(
        f"/runs/{run_id}/execute",
        json={
            "bundle_id": "esrs_mini",
            "bundle_version": "2026.01",
            "llm_provider": "deterministic_fallback",
        },
        headers=AUTH_DEFAULT,
    )
    assert execute.status_code == 200

    terminal = _wait_for_terminal_status(db_url, run_id=run_id)
    assert terminal == "completed"

    report = client.get(f"/runs/{run_id}/report-preview", headers=AUTH_DEFAULT)
    assert report.status_code == 200
