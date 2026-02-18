"""LLM health probe helpers."""

from __future__ import annotations

from apps.api.app.services.llm_extraction import OpenAICompatibleTransport


def probe_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    timeout_seconds: float = 3.0,
) -> tuple[bool, str]:
    transport = OpenAICompatibleTransport(
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )
    try:
        transport.create_response(
            model=model,
            input_text="Health check. Return a compact JSON object.",
            temperature=0.0,
            json_schema={
                "type": "object",
                "additionalProperties": True,
            },
        )
        return True, "ok"
    except Exception as exc:  # pragma: no cover - defensive runtime probe behavior
        return False, f"{type(exc).__name__}: {exc}"
