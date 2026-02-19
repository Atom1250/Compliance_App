import httpx
import pytest

from apps.api.app.services.llm_extraction import (
    ExtractionClient,
    ExtractionResult,
    ExtractionStatus,
    OpenAICompatibleTransport,
)


class MockTransport:
    def __init__(self, response_payload):
        self.response_payload = response_payload
        self.calls = []

    def create_response(self, *, model, input_text, temperature, json_schema):
        self.calls.append(
            {
                "model": model,
                "input_text": input_text,
                "temperature": temperature,
                "json_schema": json_schema,
            }
        )
        return self.response_payload


def _response_with_json(obj: dict) -> dict:
    import json

    return {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps(obj)}],
            }
        ]
    }


def test_mock_llm_extraction_enforces_temperature_zero_and_schema() -> None:
    payload = _response_with_json(
        {
            "status": "Present",
            "value": "42",
            "evidence_chunk_ids": ["chunk-1"],
            "rationale": "Value appears explicitly.",
        }
    )
    transport = MockTransport(payload)
    client = ExtractionClient(transport=transport, model="gpt-5")

    result = client.extract(datapoint_key="ESRS-E1-6", context_chunks=["chunk text"])

    assert isinstance(result, ExtractionResult)
    assert result.status == ExtractionStatus.PRESENT
    assert transport.calls[0]["temperature"] == 0.0


def test_schema_validation_rejects_invalid_status() -> None:
    payload = _response_with_json(
        {
            "status": "UNKNOWN",
            "value": None,
            "evidence_chunk_ids": [],
            "rationale": "invalid",
        }
    )
    client = ExtractionClient(transport=MockTransport(payload), model="gpt-5")

    with pytest.raises(Exception):
        client.extract(datapoint_key="ESRS-E1-6", context_chunks=["chunk text"])


def test_evidence_gating_rejects_present_without_evidence() -> None:
    payload = _response_with_json(
        {
            "status": "Present",
            "value": "42",
            "evidence_chunk_ids": [],
            "rationale": "claims presence without evidence",
        }
    )
    client = ExtractionClient(transport=MockTransport(payload), model="gpt-5")

    with pytest.raises(Exception):
        client.extract(datapoint_key="ESRS-E1-6", context_chunks=["chunk text"])


def test_openai_transport_falls_back_to_chat_completions(monkeypatch) -> None:
    calls: list[str] = []

    def _mock_post(url: str, **kwargs):
        calls.append(url)
        if url.endswith("/responses"):
            return httpx.Response(
                400,
                json={"error": {"message": "bad request"}},
                request=httpx.Request("POST", url),
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"status":"Absent","value":null,"evidence_chunk_ids":[],'  # noqa: E501
                                '"rationale":"fallback path"}'
                            )
                        }
                    }
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", _mock_post)
    transport = OpenAICompatibleTransport(base_url="https://api.openai.com/v1", api_key="test")
    payload = transport.create_response(
        model="gpt-4o-mini",
        input_text="hello",
        temperature=0.0,
        json_schema={"type": "object"},
    )
    assert calls[0].endswith("/responses")
    assert calls[1].endswith("/chat/completions")
    assert payload["output"][0]["content"][0]["type"] == "output_text"


def test_openai_transport_falls_back_to_chat_on_responses_timeout(monkeypatch) -> None:
    calls: list[str] = []

    def _mock_post(url: str, **kwargs):
        calls.append(url)
        if url.endswith("/responses"):
            raise httpx.ReadTimeout("timed out")
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"status":"Absent","value":null,"evidence_chunk_ids":[],'
                                '"rationale":"chat-timeout-fallback"}'
                            )
                        }
                    }
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", _mock_post)
    transport = OpenAICompatibleTransport(base_url="http://127.0.0.1:1234/v1", api_key="test")
    payload = transport.create_response(
        model="local-model",
        input_text="hello",
        temperature=0.0,
        json_schema={"type": "object"},
    )
    assert calls[0].endswith("/responses")
    assert calls[1].endswith("/chat/completions")
    assert payload["output"][0]["content"][0]["type"] == "output_text"


def test_openai_transport_prefers_chat_first_when_configured(monkeypatch) -> None:
    calls: list[str] = []

    def _mock_post(url: str, **kwargs):
        calls.append(url)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"status":"Absent","value":null,"evidence_chunk_ids":[],'
                                '"rationale":"chat-first"}'
                            )
                        }
                    }
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", _mock_post)
    transport = OpenAICompatibleTransport(
        base_url="http://127.0.0.1:1234/v1",
        api_key="test",
        prefer_chat_completions=True,
    )
    payload = transport.create_response(
        model="local-model",
        input_text="hello",
        temperature=0.0,
        json_schema={"type": "object"},
    )
    assert calls[0].endswith("/chat/completions")
    assert payload["output"][0]["content"][0]["type"] == "output_text"


def test_extraction_client_parses_chat_completions_shape() -> None:
    transport = MockTransport(
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"status":"Absent","value":null,"evidence_chunk_ids":[],'
                            '"rationale":"chat-shape"}'
                        )
                    }
                }
            ]
        }
    )
    client = ExtractionClient(transport=transport, model="gpt-5")
    result = client.extract(datapoint_key="ESRS-E1-6", context_chunks=["chunk text"])
    assert result.status == ExtractionStatus.ABSENT


def test_extraction_client_parses_top_level_output_text_shape() -> None:
    transport = MockTransport(
        {
            "output_text": (
                '{"status":"Absent","value":null,"evidence_chunk_ids":[],"rationale":"top-level"}'
            )
        }
    )
    client = ExtractionClient(transport=transport, model="gpt-5")
    result = client.extract(datapoint_key="ESRS-E1-6", context_chunks=["chunk text"])
    assert result.status == ExtractionStatus.ABSENT


def test_extraction_client_parses_markdown_fenced_json() -> None:
    transport = MockTransport(
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            "```json\n"
                            '{"status":"Absent","value":null,"evidence_chunk_ids":[],"rationale":"fenced"}'
                            "\n```"
                        )
                    }
                }
            ]
        }
    )
    client = ExtractionClient(transport=transport, model="gpt-5")
    result = client.extract(datapoint_key="ESRS-E1-6", context_chunks=["chunk text"])
    assert result.status == ExtractionStatus.ABSENT


def test_extraction_client_parses_responses_text_content_blocks() -> None:
    transport = MockTransport(
        {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "text",
                            "text": {
                                "value": (
                                    '{"status":"Absent","value":null,'
                                    '"evidence_chunk_ids":[],"rationale":"text-block"}'
                                )
                            },
                        }
                    ],
                }
            ]
        }
    )
    client = ExtractionClient(transport=transport, model="gpt-5")
    result = client.extract(datapoint_key="ESRS-E1-6", context_chunks=["chunk text"])
    assert result.status == ExtractionStatus.ABSENT


def test_extraction_client_normalizes_provider_error() -> None:
    class _FailingTransport:
        def create_response(self, *, model, input_text, temperature, json_schema):
            del model, input_text, temperature, json_schema
            raise RuntimeError("connection dropped")

    client = ExtractionClient(transport=_FailingTransport(), model="gpt-5")
    with pytest.raises(ValueError, match="llm_provider_error: RuntimeError: connection dropped"):
        client.extract(datapoint_key="ESRS-E1-6", context_chunks=["chunk text"])


def test_extraction_client_normalizes_schema_parse_error() -> None:
    transport = MockTransport({"output": []})
    client = ExtractionClient(transport=transport, model="gpt-5")
    with pytest.raises(ValueError, match="llm_schema_parse_error"):
        client.extract(datapoint_key="ESRS-E1-6", context_chunks=["chunk text"])


def test_extraction_client_normalizes_schema_validation_error() -> None:
    transport = MockTransport(
        _response_with_json(
            {
                "status": "Present",
                "value": "42",
                "evidence_chunk_ids": [],
                "rationale": "missing evidence for present",
            }
        )
    )
    client = ExtractionClient(transport=transport, model="gpt-5")
    with pytest.raises(ValueError, match="llm_schema_validation_error"):
        client.extract(datapoint_key="ESRS-E1-6", context_chunks=["chunk text"])
