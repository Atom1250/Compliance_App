from fastapi.testclient import TestClient

from apps.api.main import app


def test_llm_health_returns_config_without_probe(monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_LLM_BASE_URL", "http://127.0.0.1:1234")
    monkeypatch.setenv("COMPLIANCE_APP_LLM_MODEL", "ministral-3-8b-instruct-2512-mlx")

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    response = client.get("/llm-health")
    assert response.status_code == 200
    assert response.json() == {
        "provider": "local_lm_studio",
        "base_url": "http://127.0.0.1:1234",
        "model": "ministral-3-8b-instruct-2512-mlx",
        "reachable": None,
        "detail": "probe_not_requested",
    }


def test_llm_health_probe_uses_probe_result(monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_LLM_BASE_URL", "http://127.0.0.1:1234")
    monkeypatch.setenv("COMPLIANCE_APP_LLM_MODEL", "ministral-3-8b-instruct-2512-mlx")

    from apps.api.app.api.routers import system as system_router_module
    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr(
        system_router_module,
        "probe_openai_compatible",
        lambda **kwargs: (True, "ok"),
    )

    client = TestClient(app)
    response = client.get("/llm-health", params={"probe": "true"})

    assert response.status_code == 200
    assert response.json() == {
        "provider": "local_lm_studio",
        "base_url": "http://127.0.0.1:1234",
        "model": "ministral-3-8b-instruct-2512-mlx",
        "reachable": True,
        "detail": "ok",
    }


def test_llm_health_openai_provider_uses_cloud_config(monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("COMPLIANCE_APP_OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("COMPLIANCE_APP_OPENAI_API_KEY", "secret")

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    response = client.get("/llm-health", params={"provider": "openai_cloud"})

    assert response.status_code == 200
    assert response.json() == {
        "provider": "openai_cloud",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "reachable": None,
        "detail": "probe_not_requested",
    }
