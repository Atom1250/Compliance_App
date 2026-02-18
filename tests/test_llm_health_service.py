from apps.api.app.services import llm_health as llm_health_module


def test_probe_openai_compatible_accepts_non_output_text_payload(monkeypatch) -> None:
    class _DummyTransport:
        def __init__(self, **kwargs):
            del kwargs

        def create_response(self, **kwargs):
            del kwargs
            return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(llm_health_module, "OpenAICompatibleTransport", _DummyTransport)

    reachable, detail = llm_health_module.probe_openai_compatible(
        base_url="http://127.0.0.1:1234",
        api_key="lm-studio",
        model="ministral-3-8b-instruct-2512-mlx",
    )

    assert reachable is True
    assert detail == "ok"


def test_probe_openai_compatible_returns_error_detail_on_transport_failure(monkeypatch) -> None:
    class _FailingTransport:
        def __init__(self, **kwargs):
            del kwargs

        def create_response(self, **kwargs):
            del kwargs
            raise ValueError("probe failed")

    monkeypatch.setattr(llm_health_module, "OpenAICompatibleTransport", _FailingTransport)

    reachable, detail = llm_health_module.probe_openai_compatible(
        base_url="http://127.0.0.1:1234",
        api_key="lm-studio",
        model="ministral-3-8b-instruct-2512-mlx",
    )

    assert reachable is False
    assert detail == "ValueError: probe failed"
