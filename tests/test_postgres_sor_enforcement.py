import pytest

from apps.api.app.core.auth import _resolve_key_maps
from apps.api.app.core.config import get_settings
from apps.api.app.main import create_app


def _clear_caches() -> None:
    get_settings.cache_clear()
    _resolve_key_maps.cache_clear()


def test_create_app_rejects_sqlite_without_transitional_override(monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", "sqlite:///outputs/dev/compliance_app.sqlite")
    monkeypatch.setenv("COMPLIANCE_APP_RUNTIME_ENVIRONMENT", "development")
    monkeypatch.setenv("COMPLIANCE_APP_ALLOW_SQLITE_TRANSITIONAL", "false")
    _clear_caches()

    with pytest.raises(ValueError, match="sqlite backend is transitional only"):
        create_app()


def test_create_app_allows_sqlite_when_transitional_override_enabled(monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", "sqlite:///outputs/dev/compliance_app.sqlite")
    monkeypatch.setenv("COMPLIANCE_APP_RUNTIME_ENVIRONMENT", "development")
    monkeypatch.setenv("COMPLIANCE_APP_ALLOW_SQLITE_TRANSITIONAL", "true")
    _clear_caches()

    app = create_app()
    assert app.title


def test_create_app_allows_sqlite_in_test_environment(monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", "sqlite:///outputs/dev/compliance_app.sqlite")
    monkeypatch.setenv("COMPLIANCE_APP_RUNTIME_ENVIRONMENT", "test")
    monkeypatch.setenv("COMPLIANCE_APP_ALLOW_SQLITE_TRANSITIONAL", "false")
    _clear_caches()

    app = create_app()
    assert app.title
