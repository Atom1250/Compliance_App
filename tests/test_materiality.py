from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.requirements.importer import import_bundle, load_bundle
from apps.api.app.db.models import Company, Run
from apps.api.main import app


def _prepare_fixture(tmp_path: Path) -> tuple[str, int]:
    db_path = tmp_path / "materiality.sqlite"
    db_url = f"sqlite:///{db_path}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    with Session(engine, expire_on_commit=False) as session:
        import_bundle(session, load_bundle(Path("requirements/esrs_mini/bundle.json")))

        company = Company(
            name="Materiality Co",
            employees=500,
            turnover=50_000_000.0,
            listed_status=True,
            reporting_year=2026,
        )
        session.add(company)
        session.flush()

        run = Run(company_id=company.id, status="queued")
        session.add(run)
        session.commit()
        return db_url, run.id


def test_materiality_toggle_changes_required_datapoints(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id = _prepare_fixture(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    baseline = client.post(
        f"/runs/{run_id}/required-datapoints",
        json={"bundle_id": "esrs_mini", "bundle_version": "2026.01"},
    )
    assert baseline.status_code == 200
    assert baseline.json()["required_datapoint_ids"] == ["ESRS-E1-1", "ESRS-E1-6"]

    update = client.post(
        f"/runs/{run_id}/materiality",
        json={
            "entries": [
                {"topic": "climate", "is_material": False},
                {"topic": "emissions", "is_material": True},
            ]
        },
    )
    assert update.status_code == 200

    after_toggle = client.post(
        f"/runs/{run_id}/required-datapoints",
        json={"bundle_id": "esrs_mini", "bundle_version": "2026.01"},
    )
    assert after_toggle.status_code == 200
    assert after_toggle.json()["required_datapoint_ids"] == ["ESRS-E1-6"]

    re_toggle = client.post(
        f"/runs/{run_id}/materiality",
        json={
            "entries": [
                {"topic": "climate", "is_material": True},
                {"topic": "emissions", "is_material": True},
            ]
        },
    )
    assert re_toggle.status_code == 200

    after_reenable = client.post(
        f"/runs/{run_id}/required-datapoints",
        json={"bundle_id": "esrs_mini", "bundle_version": "2026.01"},
    )
    assert after_reenable.status_code == 200
    assert after_reenable.json()["required_datapoint_ids"] == ["ESRS-E1-1", "ESRS-E1-6"]
