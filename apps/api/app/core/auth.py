"""API key auth and tenant context resolution."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from fastapi import Header, HTTPException, status

from apps.api.app.core.config import get_settings


@dataclass(frozen=True)
class AuthContext:
    tenant_id: str
    api_key: str


def _parse_csv(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def _parse_tenant_keys(value: str) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = {}
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            raise ValueError(f"Invalid tenant key entry '{item}': expected tenant:key")
        tenant, key = item.split(":", 1)
        tenant = tenant.strip()
        key = key.strip()
        if not tenant or not key:
            raise ValueError(f"Invalid tenant key entry '{item}': empty tenant or key")
        mapping.setdefault(tenant, set()).add(key)
    return mapping


def validate_auth_configuration(
    *,
    security_enabled: bool,
    auth_api_keys: str,
    auth_tenant_keys: str,
) -> None:
    if not security_enabled:
        return
    global_keys = _parse_csv(auth_api_keys)
    tenant_keys = _parse_tenant_keys(auth_tenant_keys)
    if not global_keys and not tenant_keys:
        raise ValueError(
            "Invalid auth configuration: at least one API key must be configured "
            "when security is enabled"
        )


@lru_cache
def _resolve_key_maps(
    *,
    security_enabled: bool,
    auth_api_keys: str,
    auth_tenant_keys: str,
) -> tuple[set[str], dict[str, set[str]]]:
    validate_auth_configuration(
        security_enabled=security_enabled,
        auth_api_keys=auth_api_keys,
        auth_tenant_keys=auth_tenant_keys,
    )
    return _parse_csv(auth_api_keys), _parse_tenant_keys(auth_tenant_keys)


def require_auth_context(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> AuthContext:
    settings = get_settings()
    if not settings.security_enabled:
        return AuthContext(tenant_id="default", api_key="disabled")

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing api key",
        )
    tenant_id = x_tenant_id or "default"

    global_keys, tenant_keys = _resolve_key_maps(
        security_enabled=settings.security_enabled,
        auth_api_keys=settings.auth_api_keys,
        auth_tenant_keys=settings.auth_tenant_keys,
    )

    allowed_keys = tenant_keys.get(tenant_id, set()) | global_keys
    if x_api_key not in allowed_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid api key or tenant",
        )
    return AuthContext(tenant_id=tenant_id, api_key=x_api_key)
