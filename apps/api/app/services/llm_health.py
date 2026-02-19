"""LLM health probe helpers."""

from __future__ import annotations

from apps.api.app.services.llm_extraction import ExtractionClient, OpenAICompatibleTransport


def probe_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    timeout_seconds: float = 30.0,
) -> tuple[bool, str]:
    transport = OpenAICompatibleTransport(
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )
    try:
        transport.create_response(
            model=model,
            input_text='Health check. Return only JSON: {"ok": true}.',
            temperature=0.0,
            json_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {"ok": {"type": "boolean"}},
                "required": ["ok"],
            },
        )
        return True, "ok"
    except Exception as exc:  # pragma: no cover - defensive runtime probe behavior
        return False, f"{type(exc).__name__}: {exc}"


def probe_openai_compatible_detailed(
    *,
    base_url: str,
    api_key: str,
    model: str,
    timeout_seconds: float = 30.0,
) -> tuple[bool, bool, str]:
    transport = OpenAICompatibleTransport(
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )
    try:
        payload = transport.create_response(
            model=model,
            input_text='Health check. Return only JSON: {"ok": true}.',
            temperature=0.0,
            json_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {"ok": {"type": "boolean"}},
                "required": ["ok"],
            },
        )
    except Exception as exc:  # pragma: no cover - defensive runtime probe behavior
        return False, False, f"{type(exc).__name__}: {exc}"

    parse_ok = False
    parse_detail = "ok"
    try:
        ExtractionClient._extract_json_text(payload)
        parse_ok = True
    except Exception as exc:
        parse_detail = f"parse_error: {type(exc).__name__}: {exc}"

    return True, parse_ok, parse_detail if not parse_ok else "ok"
