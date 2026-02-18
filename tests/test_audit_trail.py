from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.requirements.importer import import_bundle, load_bundle
from apps.api.app.db.models import Company, Run
from apps.api.app.services.audit import log_structured_event
from apps.api.main import app

AUTH_DEFAULT = {"X-API-Key": "dev-key", "X-Tenant-ID": "default"}
AUTH_OTHER = {"X-API-Key": "dev-key", "X-Tenant-ID": "other"}


def _prepare_fixture(tmp_path: Path) -> tuple[str, int]:
    db_path = tmp_path / "audit_trail.sqlite"
    db_url = f"sqlite:///{db_path}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    with Session(engine, expire_on_commit=False) as session:
        import_bundle(session, load_bundle(Path("requirements/esrs_mini/bundle.json")))
        company = Company(
            name="Audit Co",
            tenant_id="default",
            employees=500,
            turnover=50_000_000.0,
            listed_status=True,
            reporting_year=2026,
        )
        session.add(company)
        session.flush()
        run = Run(company_id=company.id, tenant_id="default", status="queued")
        session.add(run)
        session.commit()
        return db_url, run.id


def test_structured_log_payload_is_deterministic() -> None:
    payload = log_structured_event("run.tested", run_id=7, tenant_id="default")
    assert payload == '{"event_type":"run.tested","run_id":7,"tenant_id":"default"}'


def test_run_event_history_is_complete_and_ordered(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id = _prepare_fixture(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    required = client.post(
        f"/runs/{run_id}/required-datapoints",
        json={"bundle_id": "esrs_mini", "bundle_version": "2026.01"},
        headers=AUTH_DEFAULT,
    )
    assert required.status_code == 200

    update = client.post(
        f"/runs/{run_id}/materiality",
        json={"entries": [{"topic": "climate", "is_material": False}]},
        headers=AUTH_DEFAULT,
    )
    assert update.status_code == 200

    events = client.get(f"/runs/{run_id}/events", headers=AUTH_DEFAULT)
    assert events.status_code == 200
    payload = events.json()

    event_types = [item["event_type"] for item in payload["events"]]
    assert event_types == ["required_datapoints.resolved", "materiality.updated"]
    assert payload["events"][0]["payload"]["bundle_id"] == "esrs_mini"
    assert payload["events"][1]["payload"]["topics"] == ["climate"]


def test_run_event_history_is_tenant_scoped(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id = _prepare_fixture(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    response = client.get(f"/runs/{run_id}/events", headers=AUTH_OTHER)
    assert response.status_code == 404
