"""Minimal HTTP JSON-RPC client for NotebookLM MCP endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import count
from typing import Any

import httpx

from apps.api.app.integrations.notebooklm.errors import (
    NotebookLMMCPResponseError,
    NotebookLMMCPTransportError,
)

_REQUEST_ID = count(1)


@dataclass(frozen=True)
class NotebookLMMCPClient:
    base_url: str
    timeout_seconds: float = 30.0
    retries: int = 1

    def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": next(_REQUEST_ID),
            "method": method,
            "params": params or {},
        }
        attempts = max(self.retries, 0) + 1
        last_error: Exception | None = None

        for _ in range(attempts):
            try:
                response = httpx.post(
                    self.base_url,
                    json=payload,
                    timeout=httpx.Timeout(self.timeout_seconds),
                )
                response.raise_for_status()
                body = response.json()
                if not isinstance(body, dict):
                    raise NotebookLMMCPResponseError("MCP response body must be a JSON object")
                if "error" in body and body["error"] is not None:
                    raise NotebookLMMCPResponseError(f"MCP error response: {body['error']}")
                if "result" not in body:
                    raise NotebookLMMCPResponseError("MCP response missing 'result' field")
                return body["result"]
            except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as exc:
                last_error = exc
            except ValueError as exc:
                raise NotebookLMMCPResponseError("MCP returned invalid JSON payload") from exc

        raise NotebookLMMCPTransportError(
            f"NotebookLM MCP request failed after {attempts} attempt(s)"
        ) from last_error
