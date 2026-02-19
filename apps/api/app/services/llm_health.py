"""LLM health probe helpers."""

from __future__ import annotations

import json

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


def probe_openai_compatible_detailed(
    *,
    base_url: str,
    api_key: str,
    model: str,
    timeout_seconds: float = 3.0,
) -> tuple[bool, bool, str]:
    transport = OpenAICompatibleTransport(
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )
    try:
        payload = transport.create_response(
            model=model,
            input_text="Health check. Return a compact JSON object.",
            temperature=0.0,
            json_schema={
                "type": "object",
                "additionalProperties": True,
            },
        )
    except Exception as exc:  # pragma: no cover - defensive runtime probe behavior
        return False, False, f"{type(exc).__name__}: {exc}"

    parse_ok = False
    parse_detail = "ok"
    try:
        output_items = payload.get("output", [])
        for item in output_items:
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    json.loads(content["text"])
                    parse_ok = True
                    break
            if parse_ok:
                break
        if not parse_ok:
            choices = payload.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                if isinstance(content, list):
                    content = "".join(
                        str(item.get("text", "")) for item in content if isinstance(item, dict)
                    )
                if isinstance(content, str):
                    json.loads(content)
                    parse_ok = True
    except Exception as exc:
        parse_detail = f"parse_error: {type(exc).__name__}: {exc}"

    return True, parse_ok, parse_detail if not parse_ok else "ok"
