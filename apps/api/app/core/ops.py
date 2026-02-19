"""Operational safety helpers for request handling and config validation."""

from __future__ import annotations

import os
from typing import Any

from apps.api.app.core.config import Settings

_REDACTED = "***REDACTED***"
_SENSITIVE_KEYS = {"api_key", "authorization", "token", "secret", "password", "llm_api_key"}


def _is_sensitive_key(key: str) -> bool:
    key_lower = key.lower()
    normalized = key_lower.replace("-", "_")
    return (
        normalized in _SENSITIVE_KEYS
        or normalized.endswith("_key")
        or normalized.endswith("apikey")
        or "authorization" in normalized
    )


def redact_sensitive_fields(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, nested in value.items():
            if _is_sensitive_key(key):
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
    if settings.openai_base_url and not settings.openai_base_url.startswith(("http://", "https://")):
        raise ValueError("Invalid runtime configuration: openai base url must be http(s)")

    provider_list = sorted(
        {
            item.strip()
            for item in settings.startup_validate_providers.split(",")
            if item.strip()
        }
    )
    valid = {"local_lm_studio", "openai_cloud", "tavily"}
    unknown = [item for item in provider_list if item not in valid]
    if unknown:
        raise ValueError(
            "Invalid runtime configuration: unknown startup provider checks: "
            + ",".join(unknown)
        )

    if "local_lm_studio" in provider_list:
        if not settings.llm_base_url:
            raise ValueError(
                "Invalid runtime configuration: llm_base_url is required for local_lm_studio"
            )
        if not settings.llm_model:
            raise ValueError(
                "Invalid runtime configuration: llm_model is required for local_lm_studio"
            )
        if not settings.llm_api_key:
            raise ValueError(
                "Invalid runtime configuration: llm_api_key is required for local_lm_studio"
            )

    if "openai_cloud" in provider_list:
        if not settings.openai_base_url:
            raise ValueError(
                "Invalid runtime configuration: openai_base_url is required for openai_cloud"
            )
        if not settings.openai_model:
            raise ValueError(
                "Invalid runtime configuration: openai_model is required for openai_cloud"
            )
        if not (settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")):
            raise ValueError(
                "Invalid runtime configuration: openai_api_key is required for openai_cloud"
            )

    if "tavily" in provider_list:
        if not settings.tavily_enabled:
            raise ValueError(
                "Invalid runtime configuration: tavily_enabled must be true for tavily"
            )
        if not settings.tavily_api_key:
            raise ValueError(
                "Invalid runtime configuration: tavily_api_key is required for tavily"
            )
