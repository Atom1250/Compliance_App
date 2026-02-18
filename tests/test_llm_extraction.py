import pytest

from apps.api.app.services.llm_extraction import (
    ExtractionClient,
    ExtractionResult,
    ExtractionStatus,
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
