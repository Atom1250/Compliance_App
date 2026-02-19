"""Deterministic, schema-enforced LLM extraction service."""

from __future__ import annotations

import json
import re
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

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 30.0,
        prefer_chat_completions: bool = False,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._prefer_chat_completions = prefer_chat_completions

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _request_responses(
        self, *, model: str, input_text: str, temperature: float, json_schema: dict[str, Any]
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
        response = httpx.post(
            f"{self._base_url}/responses",
            headers=self._headers(),
            json=payload,
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def _request_chat_completions(
        self, *, model: str, input_text: str, temperature: float, json_schema: dict[str, Any]
    ) -> dict[str, Any]:
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
            headers=self._headers(),
            json=chat_payload,
            timeout=self._timeout_seconds,
        )
        chat_response.raise_for_status()
        chat_json = chat_response.json()
        content_text = chat_json.get("choices", [{}])[0].get("message", {}).get("content", "")
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

    def create_response(
        self,
        *,
        model: str,
        input_text: str,
        temperature: float,
        json_schema: dict[str, Any],
    ) -> dict[str, Any]:
        endpoint_order = (
            ("chat", "responses") if self._prefer_chat_completions else ("responses", "chat")
        )
        errors: dict[str, str] = {}
        last_exc: Exception | None = None
        for endpoint in endpoint_order:
            try:
                if endpoint == "responses":
                    return self._request_responses(
                        model=model,
                        input_text=input_text,
                        temperature=temperature,
                        json_schema=json_schema,
                    )
                return self._request_chat_completions(
                    model=model,
                    input_text=input_text,
                    temperature=temperature,
                    json_schema=json_schema,
                )
            except Exception as exc:  # pragma: no cover - network/runtime behavior
                last_exc = exc
                errors[endpoint] = f"{type(exc).__name__}: {exc}"
                continue

        detail = "; ".join(
            [
                f"/responses {errors.get('responses', 'not attempted')}",
                f"/chat/completions {errors.get('chat', 'not attempted')}",
            ]
        )
        if isinstance(last_exc, httpx.HTTPStatusError):
            raise httpx.HTTPStatusError(
                f"LLM request failed: {detail}",
                request=last_exc.request,
                response=last_exc.response,
            ) from last_exc
        raise RuntimeError(f"LLM request failed: {detail}") from last_exc


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
        try:
            response_payload = self._transport.create_response(
                model=self._model,
                input_text=prompt,
                temperature=0.0,
                json_schema=ExtractionResult.model_json_schema(),
            )
        except Exception as exc:
            raise ValueError(f"llm_provider_error: {type(exc).__name__}: {exc}") from exc

        try:
            parsed = self._extract_json_text(response_payload)
        except Exception as exc:
            raise ValueError(f"llm_schema_parse_error: {type(exc).__name__}: {exc}") from exc

        try:
            return ExtractionResult.model_validate(parsed)
        except Exception as exc:
            raise ValueError(f"llm_schema_validation_error: {type(exc).__name__}: {exc}") from exc

    @staticmethod
    def _json_from_text(text: str) -> dict[str, Any]:
        text = text.strip()
        if not text:
            raise ValueError("empty text payload")
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
        if fenced_match:
            parsed = json.loads(fenced_match.group(1))
            if isinstance(parsed, dict):
                return parsed

        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and first < last:
            parsed = json.loads(text[first : last + 1])
            if isinstance(parsed, dict):
                return parsed

        raise ValueError("text payload does not contain a JSON object")

    @staticmethod
    def _coerce_content_text(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts: list[str] = []
            for item in value:
                if isinstance(item, dict):
                    text_value = item.get("text")
                    if isinstance(text_value, str):
                        parts.append(text_value)
                    elif isinstance(text_value, dict) and isinstance(text_value.get("value"), str):
                        parts.append(text_value["value"])
                    elif isinstance(item.get("content"), str):
                        parts.append(item["content"])
            return "".join(parts)
        if isinstance(value, dict):
            text_value = value.get("text")
            if isinstance(text_value, str):
                return text_value
            if isinstance(text_value, dict) and isinstance(text_value.get("value"), str):
                return text_value["value"]
            if isinstance(value.get("content"), str):
                return value["content"]
        return ""

    @staticmethod
    def build_prompt(*, datapoint_key: str, context_chunks: list[str]) -> str:
        chunks_text = "\n\n".join(context_chunks)
        return (
            f"Assess datapoint {datapoint_key}. Return JSON only matching schema.\n"
            f"Context chunks:\n{chunks_text}"
        )

    @staticmethod
    def _extract_json_text(response_payload: dict[str, Any]) -> dict[str, Any]:
        # Top-level OpenAI-compatible output text variant.
        if isinstance(response_payload.get("output_text"), str):
            return ExtractionClient._json_from_text(response_payload["output_text"])

        # `/responses` API shape.
        output_items = response_payload.get("output", [])
        for item in output_items:
            if item.get("type") == "output_text":
                text = ExtractionClient._coerce_content_text(item.get("text", ""))
                if text.strip():
                    return ExtractionClient._json_from_text(text)
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                text = ExtractionClient._coerce_content_text(content)
                if content.get("type") in {"output_text", "text"} and text.strip():
                    return ExtractionClient._json_from_text(text)

        # Native `/chat/completions` shape.
        choices = response_payload.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            if isinstance(message.get("parsed"), dict):
                return message["parsed"]

            content = ExtractionClient._coerce_content_text(message.get("content", ""))
            if content.strip():
                return ExtractionClient._json_from_text(content)

        raise ValueError("No JSON extraction payload found in provider response")
