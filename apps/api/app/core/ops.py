"""Operational safety helpers for request handling and config validation."""

from __future__ import annotations

from typing import Any

from apps.api.app.core.config import Settings

_REDACTED = "***REDACTED***"
_SENSITIVE_KEYS = {"api_key", "authorization", "token", "secret", "password", "llm_api_key"}


def redact_sensitive_fields(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, nested in value.items():
            key_lower = key.lower()
            if key_lower in _SENSITIVE_KEYS or key_lower.endswith("_key"):
                redacted[key] = _REDACTED
            else:
                redacted[key] = redact_sensitive_fields(nested)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive_fields(item) for item in value]
    return value


def validate_runtime_configuration(settings: Settings) -> None:
    if settings.request_rate_limit_window_seconds <= 0:
        raise ValueError("Invalid runtime configuration: rate limit window must be > 0")
    if settings.request_rate_limit_max_requests <= 0:
        raise ValueError("Invalid runtime configuration: rate limit max requests must be > 0")
    if not settings.llm_base_url.startswith(("http://", "https://")):
        raise ValueError("Invalid runtime configuration: llm base url must be http(s)")
