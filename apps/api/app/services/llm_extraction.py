"""Deterministic, schema-enforced LLM extraction service."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExtractionStatus(str, Enum):
    PRESENT = "Present"
    PARTIAL = "Partial"
    ABSENT = "Absent"
    NA = "NA"


class ExtractionResult(BaseModel):
    """Schema-only extraction result."""

    model_config = ConfigDict(extra="forbid")

    status: ExtractionStatus
    value: str | None = None
    evidence_chunk_ids: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_evidence_gating(self) -> ExtractionResult:
        if (
            self.status in {ExtractionStatus.PRESENT, ExtractionStatus.PARTIAL}
            and not self.evidence_chunk_ids
        ):
            raise ValueError("Present/Partial status requires evidence_chunk_ids")
        return self


class LLMTransport(Protocol):
    """OpenAI-compatible transport contract."""

    def create_response(
        self,
        *,
        model: str,
        input_text: str,
        temperature: float,
        json_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Return response payload from an OpenAI-compatible backend."""


class OpenAICompatibleTransport:
    """HTTP transport for OpenAI-compatible `/responses` API."""

    def __init__(self, *, base_url: str, api_key: str, timeout_seconds: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    def create_response(
        self,
        *,
        model: str,
        input_text: str,
        temperature: float,
        json_schema: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "input": input_text,
            "temperature": temperature,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "extraction_result",
                    "schema": json_schema,
                }
            },
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        response = httpx.post(
            f"{self._base_url}/responses",
            headers=headers,
            json=payload,
            timeout=self._timeout_seconds,
        )
        if response.status_code < 400:
            return response.json()

        # Some OpenAI models/accounts reject `/responses` payload variants.
        # Fall back to `/chat/completions` with JSON schema response format.
        chat_payload = {
            "model": model,
            "messages": [{"role": "user", "content": input_text}],
            "temperature": temperature,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "extraction_result",
                    "schema": json_schema,
                },
            },
        }
        chat_response = httpx.post(
            f"{self._base_url}/chat/completions",
            headers=headers,
            json=chat_payload,
            timeout=self._timeout_seconds,
        )
        if chat_response.status_code < 400:
            chat_json = chat_response.json()
            content_text = (
                chat_json.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            if isinstance(content_text, list):
                content_text = "".join(
                    str(item.get("text", "")) for item in content_text if isinstance(item, dict)
                )
            return {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": str(content_text)}],
                    }
                ]
            }

        detail = (
            f"/responses {response.status_code}: {response.text}; "
            f"/chat/completions {chat_response.status_code}: {chat_response.text}"
        )
        raise httpx.HTTPStatusError(
            f"LLM request failed: {detail}",
            request=chat_response.request,
            response=chat_response,
        )


class ExtractionClient:
    """Deterministic extraction client that enforces schema and temperature=0."""

    def __init__(self, *, transport: LLMTransport, model: str) -> None:
        self._transport = transport
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def extract(self, *, datapoint_key: str, context_chunks: list[str]) -> ExtractionResult:
        prompt = self.build_prompt(datapoint_key=datapoint_key, context_chunks=context_chunks)
        response_payload = self._transport.create_response(
            model=self._model,
            input_text=prompt,
            temperature=0.0,
            json_schema=ExtractionResult.model_json_schema(),
        )
        parsed = self._extract_json_text(response_payload)
        return ExtractionResult.model_validate(parsed)

    @staticmethod
    def build_prompt(*, datapoint_key: str, context_chunks: list[str]) -> str:
        chunks_text = "\n\n".join(context_chunks)
        return (
            f"Assess datapoint {datapoint_key}. Return JSON only matching schema.\n"
            f"Context chunks:\n{chunks_text}"
        )

    @staticmethod
    def _extract_json_text(response_payload: dict[str, Any]) -> dict[str, Any]:
        output_items = response_payload.get("output", [])
        for item in output_items:
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    return json.loads(content["text"])
        raise ValueError("No JSON output_text found in response payload")
