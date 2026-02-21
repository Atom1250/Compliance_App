"""NotebookLM-backed research provider implementation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from time import monotonic
from typing import Any

from apps.api.app.core.config import Settings
from apps.api.app.integrations.notebooklm.errors import (
    NotebookLMMissingNotebookMappingError,
)
from apps.api.app.integrations.notebooklm.mcp_client import NotebookLMMCPClient
from apps.api.app.integrations.notebooklm.parser import parse_notebooklm_response
from apps.api.app.services.regulatory_research.hash import compute_request_hash
from apps.api.app.services.regulatory_research.provider import ResearchProvider
from apps.api.app.services.regulatory_research.types import ResearchRequest, ResearchResponse


@dataclass(frozen=True)
class NotebookLMProvider(ResearchProvider):
    client: NotebookLMMCPClient
    notebook_map: dict[str, str]

    def query(self, req: ResearchRequest) -> ResearchResponse:
        notebook_id = self.notebook_map.get(req.corpus_key)
        if not notebook_id:
            raise NotebookLMMissingNotebookMappingError(
                f"No notebook mapping configured for corpus key '{req.corpus_key}'"
            )

        started = monotonic()
        self.client.request("navigate_to_notebook", {"notebook_id": notebook_id})
        chat_result = self.client.request(
            "chat_with_notebook",
            {
                "notebook_id": notebook_id,
                "message": _build_prompt(req),
            },
        )
        content = _extract_content(chat_result)
        parsed = parse_notebooklm_response(content)
        latency_ms = int((monotonic() - started) * 1000)
        return ResearchResponse(
            answer_markdown=parsed.answer_markdown,
            citations=parsed.citations,
            provider="notebooklm",
            latency_ms=latency_ms,
            request_hash=compute_request_hash(req),
            confidence=None,
            can_persist=bool(parsed.citations),
        )


def build_notebooklm_provider(settings: Settings) -> NotebookLMProvider:
    notebook_map = parse_notebook_map(settings.notebooklm_notebook_map_json)
    return NotebookLMProvider(
        client=NotebookLMMCPClient(
            base_url=settings.notebooklm_mcp_base_url,
            timeout_seconds=settings.notebooklm_mcp_timeout_seconds,
            retries=settings.notebooklm_mcp_retries,
        ),
        notebook_map=notebook_map,
    )


def parse_notebook_map(value: str) -> dict[str, str]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid NOTEBOOKLM_NOTEBOOK_MAP_JSON; expected JSON object") from exc
    if not isinstance(payload, dict):
        raise ValueError("NOTEBOOKLM_NOTEBOOK_MAP_JSON must be a JSON object")

    parsed: dict[str, str] = {}
    for key, notebook_id in payload.items():
        if not isinstance(key, str) or not key.strip():
            continue
        if not isinstance(notebook_id, str) or not notebook_id.strip():
            continue
        parsed[key.strip()] = notebook_id.strip()
    return parsed


def _build_prompt(req: ResearchRequest) -> str:
    tags = ", ".join(req.tags) if req.tags else "none"
    requirement_id = req.requirement_id or "none"
    return "\n".join(
        [
            "You are a regulatory research assistant.",
            f"Mode: {req.mode}",
            f"Requirement ID: {requirement_id}",
            f"Tags: {tags}",
            "",
            "Question:",
            req.question.strip(),
            "",
            "Return a concise markdown answer.",
            "End with a section titled exactly 'CITATIONS:'",
            "Use bullet lines in this format:",
            "- Source Title | Locator (page/section) | URL (optional) | Quote (optional short)",
        ]
    )


def _extract_content(chat_result: Any) -> str:
    if isinstance(chat_result, str):
        return chat_result
    if isinstance(chat_result, dict):
        for key in ("content", "text", "answer", "response", "markdown"):
            value = chat_result.get(key)
            if isinstance(value, str):
                return value
    if isinstance(chat_result, list):
        chunks: list[str] = []
        for item in chat_result:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        if chunks:
            return "\n".join(chunks)
    return str(chat_result)
