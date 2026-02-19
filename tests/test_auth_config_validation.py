import pytest

from apps.api.app.core.auth import _resolve_key_maps, validate_auth_configuration
from apps.api.app.core.config import get_settings
from apps.api.app.main import create_app


def test_validate_auth_configuration_accepts_valid_mapping() -> None:
    validate_auth_configuration(
        security_enabled=True,
        auth_api_keys="global-key",
        auth_tenant_keys="tenant-a:key-a,tenant-b:key-b",
    )


def test_validate_auth_configuration_rejects_malformed_tenant_entry() -> None:
    with pytest.raises(ValueError, match="expected tenant:key"):
        validate_auth_configuration(
            security_enabled=True,
            auth_api_keys="",
            auth_tenant_keys="tenant-a-key-a",
        )


def test_validate_auth_configuration_rejects_empty_keys_when_enabled() -> None:
    with pytest.raises(ValueError, match="at least one API key"):
        validate_auth_configuration(
            security_enabled=True,
            auth_api_keys="",
            auth_tenant_keys="",
        )


def test_validate_auth_configuration_allows_empty_when_security_disabled() -> None:
    validate_auth_configuration(
        security_enabled=False,
        auth_api_keys="",
        auth_tenant_keys="",
    )


def test_resolve_key_maps_is_deterministic() -> None:
    _resolve_key_maps.cache_clear()
    first = _resolve_key_maps(
        security_enabled=True,
        auth_api_keys="global-key",
        auth_tenant_keys="tenant-a:key-a,tenant-a:key-a",
    )
    second = _resolve_key_maps(
        security_enabled=True,
        auth_api_keys="global-key",
        auth_tenant_keys="tenant-a:key-a,tenant-a:key-a",
    )

    assert first == second
    assert first[0] == {"global-key"}
    assert first[1] == {"tenant-a": {"key-a"}}


def test_create_app_fails_fast_on_invalid_tenant_mapping(monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_SECURITY_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCE_APP_AUTH_API_KEYS", "")
    monkeypatch.setenv("COMPLIANCE_APP_AUTH_TENANT_KEYS", "tenant-a-key-a")
    get_settings.cache_clear()
    _resolve_key_maps.cache_clear()

    with pytest.raises(ValueError, match="expected tenant:key"):
        create_app()


def test_create_app_fails_fast_on_invalid_rate_limit_window(monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_REQUEST_RATE_LIMIT_WINDOW_SECONDS", "0")
    get_settings.cache_clear()
    _resolve_key_maps.cache_clear()

    with pytest.raises(ValueError, match="rate limit window must be > 0"):
        create_app()


def test_create_app_fails_fast_on_unknown_startup_provider_check(monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_STARTUP_VALIDATE_PROVIDERS", "unknown")
    get_settings.cache_clear()
    _resolve_key_maps.cache_clear()

    with pytest.raises(ValueError, match="unknown startup provider checks"):
        create_app()


def test_create_app_fails_fast_on_missing_openai_key_when_check_enabled(monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_STARTUP_VALIDATE_PROVIDERS", "openai_cloud")
    monkeypatch.setenv("COMPLIANCE_APP_OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("COMPLIANCE_APP_OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("COMPLIANCE_APP_OPENAI_API_KEY", "")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    _resolve_key_maps.cache_clear()

    with pytest.raises(ValueError, match="openai_api_key is required for openai_cloud"):
        create_app()


def test_create_app_fails_fast_on_tavily_check_without_enabled(monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_STARTUP_VALIDATE_PROVIDERS", "tavily")
    monkeypatch.setenv("COMPLIANCE_APP_TAVILY_ENABLED", "false")
    monkeypatch.setenv("COMPLIANCE_APP_TAVILY_API_KEY", "")
    get_settings.cache_clear()
    _resolve_key_maps.cache_clear()

    with pytest.raises(ValueError, match="tavily_enabled must be true for tavily"):
        create_app()


def test_create_app_accepts_provider_checks_when_required_keys_present(monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_STARTUP_VALIDATE_PROVIDERS", "local_lm_studio,openai_cloud")
    monkeypatch.setenv("COMPLIANCE_APP_LLM_BASE_URL", "http://127.0.0.1:1234")
    monkeypatch.setenv("COMPLIANCE_APP_LLM_MODEL", "ministral-3-8b-instruct-2512-mlx")
    monkeypatch.setenv("COMPLIANCE_APP_LLM_API_KEY", "lm-studio")
    monkeypatch.setenv("COMPLIANCE_APP_OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("COMPLIANCE_APP_OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("COMPLIANCE_APP_OPENAI_API_KEY", "secret")
    get_settings.cache_clear()
    _resolve_key_maps.cache_clear()

    app = create_app()
    assert app.title
