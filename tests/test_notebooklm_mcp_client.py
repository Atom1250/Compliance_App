import httpx
import pytest

from apps.api.app.integrations.notebooklm.errors import NotebookLMMCPTransportError
from apps.api.app.integrations.notebooklm.mcp_client import NotebookLMMCPClient


def test_mcp_client_retries_transport_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"count": 0}

    def _post(url: str, *, json: dict[str, object], timeout: httpx.Timeout) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise httpx.ConnectError("down")
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": json["id"], "result": {"ok": True}},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("apps.api.app.integrations.notebooklm.mcp_client.httpx.post", _post)
    client = NotebookLMMCPClient(base_url="http://mcp", retries=1)
    result = client.request("chat_with_notebook", {"notebook_id": "abc"})
    assert result == {"ok": True}
    assert attempts["count"] == 2


def test_mcp_client_raises_transport_after_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    def _post(url: str, *, json: dict[str, object], timeout: httpx.Timeout) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr("apps.api.app.integrations.notebooklm.mcp_client.httpx.post", _post)
    client = NotebookLMMCPClient(base_url="http://mcp", retries=1)
    with pytest.raises(NotebookLMMCPTransportError):
        client.request("chat_with_notebook", {"notebook_id": "abc"})
