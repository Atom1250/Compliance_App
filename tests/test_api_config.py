from fastapi.testclient import TestClient

from apps.api.app.core.config import get_settings
from apps.api.main import app


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_APP_VERSION", "9.9.9")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.app_version == "9.9.9"


def test_version_endpoint_uses_settings(monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_APP_VERSION", "2.1.0")
    get_settings.cache_clear()
    client = TestClient(app)

    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {"version": "2.1.0"}
