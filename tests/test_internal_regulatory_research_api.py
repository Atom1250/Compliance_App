from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from alembic import command
from alembic.config import Config
from apps.api.main import app

AUTH_DEFAULT = {"X-API-Key": "dev-key", "X-Tenant-ID": "default"}


def _prepare_db(tmp_path: Path) -> str:
    db_path = tmp_path / "internal_research.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    return db_url


def test_internal_research_route_returns_404_when_feature_disabled(
    monkeypatch, tmp_path: Path
) -> None:
    db_url = _prepare_db(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    monkeypatch.setenv("COMPLIANCE_APP_FEATURE_REG_RESEARCH_ENABLED", "false")

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    response = client.post(
        "/internal/regulatory-research/query",
        headers=AUTH_DEFAULT,
        json={
            "question": "What is CSRD phase-in?",
            "corpus_key": "EU-CSRD-ESRS",
            "mode": "qa",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "regulatory research feature disabled"


def test_internal_research_route_uses_stub_when_notebook_disabled(
    monkeypatch, tmp_path: Path
) -> None:
    db_url = _prepare_db(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    monkeypatch.setenv("COMPLIANCE_APP_FEATURE_REG_RESEARCH_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCE_APP_FEATURE_NOTEBOOKLM_ENABLED", "false")

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    response = client.post(
        "/internal/regulatory-research/query",
        headers=AUTH_DEFAULT,
        json={
            "question": "Map ESRS E1-1",
            "corpus_key": "EU-CSRD-ESRS",
            "mode": "mapping",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "stub"
    assert len(payload["citations"]) >= 1
