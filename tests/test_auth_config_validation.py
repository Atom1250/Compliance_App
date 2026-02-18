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
