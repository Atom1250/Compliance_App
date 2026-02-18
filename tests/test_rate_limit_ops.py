from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.requirements.importer import import_bundle, load_bundle
from apps.api.app.db.models import Chunk, Company, Document, DocumentFile, Run
from apps.api.app.main import create_app


def _prepare_fixture(tmp_path: Path) -> tuple[str, int]:
    db_path = tmp_path / "rate_limit.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    with Session(engine, expire_on_commit=False) as session:
        import_bundle(session, load_bundle(Path("requirements/esrs_mini/bundle.json")))
        company = Company(
            name="Rate Limit Co",
            tenant_id="default",
            employees=100,
            turnover=1_000_000.0,
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
                sha256_hash="b" * 64,
                storage_uri="file://object-store/default/b.pdf",
            )
        )
        session.add(
            Chunk(
                document_id=document.id,
                chunk_id="rate-limit-chunk-1",
                page_number=1,
                start_offset=0,
                end_offset=64,
                text="Transition plan and gross emissions are discussed.",
                content_tsv="transition plan gross emissions",
            )
        )
        session.commit()
        return db_url, run.id


def test_sensitive_route_rate_limit_returns_429(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id = _prepare_fixture(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    monkeypatch.setenv("COMPLIANCE_APP_REQUEST_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCE_APP_REQUEST_RATE_LIMIT_MAX_REQUESTS", "1")
    monkeypatch.setenv("COMPLIANCE_APP_REQUEST_RATE_LIMIT_WINDOW_SECONDS", "60")

    from apps.api.app.api.routers import materiality as materiality_router_module
    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    # Keep request behavior deterministic for throttling test.
    monkeypatch.setattr(
        materiality_router_module,
        "enqueue_run_execution",
        lambda *args, **kwargs: None,
    )

    client = TestClient(create_app())
    headers = {"X-API-Key": "dev-key", "X-Tenant-ID": "default"}
    payload = {"bundle_id": "esrs_mini", "bundle_version": "2026.01"}

    first = client.post(f"/runs/{run_id}/execute", json=payload, headers=headers)
    assert first.status_code == 200
    assert "X-Request-ID" in first.headers

    second = client.post(f"/runs/{run_id}/execute", json=payload, headers=headers)
    assert second.status_code == 429
    assert second.json()["detail"] == "rate limit exceeded"
    assert second.json()["request_id"]
    assert second.headers["X-Request-ID"] == second.json()["request_id"]
