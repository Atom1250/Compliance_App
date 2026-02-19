from pathlib import Path

from fastapi.testclient import TestClient


class _DummySession:
    def close(self) -> None:
        return None


def test_startup_sync_is_gated_off_by_default(monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_REGULATORY_REGISTRY_SYNC_ENABLED", "false")
    from apps.api.app import main as main_module
    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    called = {"count": 0}

    def _fake_sync(*args, **kwargs):
        del args, kwargs
        called["count"] += 1
        return []

    monkeypatch.setattr(main_module, "sync_from_filesystem", _fake_sync)

    with TestClient(main_module.create_app()) as client:
        response = client.get("/healthz")
        assert response.status_code == 200

    assert called["count"] == 0


def test_startup_sync_runs_when_flag_enabled(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_REGULATORY_REGISTRY_SYNC_ENABLED", "true")
    monkeypatch.setenv(
        "COMPLIANCE_APP_REGULATORY_REGISTRY_BUNDLES_ROOT",
        str(tmp_path / "bundles"),
    )
    from apps.api.app import main as main_module
    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    called = {"count": 0}

    def _fake_sync(session, *, bundles_root: Path):
        del session
        assert bundles_root == (tmp_path / "bundles")
        called["count"] += 1
        return []

    monkeypatch.setattr(main_module, "sync_from_filesystem", _fake_sync)
    monkeypatch.setattr(main_module, "get_session_factory", lambda: (lambda: _DummySession()))

    with TestClient(main_module.create_app()) as client:
        response = client.get("/healthz")
        assert response.status_code == 200

    assert called["count"] == 1

