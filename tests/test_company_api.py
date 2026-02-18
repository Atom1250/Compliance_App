from pathlib import Path

from fastapi.testclient import TestClient

from alembic import command
from alembic.config import Config
from apps.api.main import app

AUTH_DEFAULT = {"X-API-Key": "dev-key", "X-Tenant-ID": "default"}
AUTH_OTHER = {"X-API-Key": "dev-key", "X-Tenant-ID": "other"}


def _prepare_db(tmp_path: Path) -> str:
    db_path = tmp_path / "company_api.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    return db_url


def test_company_create_and_list_happy_path(monkeypatch, tmp_path: Path) -> None:
    db_url = _prepare_db(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    first = client.post(
        "/companies",
        json={
            "name": "Beta Co",
            "employees": 120,
            "reporting_year_start": 2022,
            "reporting_year_end": 2024,
        },
        headers=AUTH_DEFAULT,
    )
    second = client.post(
        "/companies",
        json={"name": "Alpha Co", "employees": 80, "reporting_year": 2026},
        headers=AUTH_DEFAULT,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    first_payload = first.json()
    assert first_payload["reporting_year"] == 2024
    assert first_payload["reporting_year_start"] == 2022
    assert first_payload["reporting_year_end"] == 2024

    listed = client.get("/companies", headers=AUTH_DEFAULT)
    assert listed.status_code == 200
    payload = listed.json()
    assert [item["name"] for item in payload["companies"]] == ["Alpha Co", "Beta Co"]


def test_company_create_rejects_invalid_reporting_year_range(monkeypatch, tmp_path: Path) -> None:
    db_url = _prepare_db(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    response = client.post(
        "/companies",
        json={
            "name": "Bad Range Co",
            "reporting_year_start": 2026,
            "reporting_year_end": 2024,
        },
        headers=AUTH_DEFAULT,
    )

    assert response.status_code == 422


def test_company_list_is_tenant_scoped(monkeypatch, tmp_path: Path) -> None:
    db_url = _prepare_db(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    created = client.post("/companies", json={"name": "Tenant A Co"}, headers=AUTH_DEFAULT)
    assert created.status_code == 200

    tenant_a = client.get("/companies", headers=AUTH_DEFAULT)
    tenant_b = client.get("/companies", headers=AUTH_OTHER)

    assert tenant_a.status_code == 200
    assert tenant_b.status_code == 200
    assert len(tenant_a.json()["companies"]) == 1
    assert tenant_a.json()["companies"][0]["name"] == "Tenant A Co"
    assert tenant_b.json()["companies"] == []
