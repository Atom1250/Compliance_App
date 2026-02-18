"""Local LLM health probe helpers."""

from __future__ import annotations

from apps.api.app.services.llm_extraction import ExtractionClient, OpenAICompatibleTransport


def probe_local_llm(
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
    client = ExtractionClient(transport=transport, model=model)
    try:
        client.extract(datapoint_key="llm.health", context_chunks=["health-check context"])
        return True, "ok"
    except Exception as exc:  # pragma: no cover - defensive runtime probe behavior
        return False, f"{type(exc).__name__}: {exc}"
