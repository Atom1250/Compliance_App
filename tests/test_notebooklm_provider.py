import pytest

from apps.api.app.core.config import Settings
from apps.api.app.integrations.notebooklm.errors import NotebookLMMissingNotebookMappingError
from apps.api.app.integrations.notebooklm.provider import NotebookLMProvider, parse_notebook_map
from apps.api.app.services.regulatory_research.types import ResearchRequest


class _FakeMCPClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []

    def request(self, method: str, params: dict[str, str] | None = None) -> str:
        payload = params or {}
        self.calls.append((method, payload))
        if method == "chat_with_notebook":
            return (
                "Answer body.\n\n"
                "CITATIONS:\n"
                "- ESRS 1 | Section 3 | https://example.org | Quoted support\n"
            )
        return "ok"


def test_provider_calls_mcp_methods_in_order() -> None:
    client = _FakeMCPClient()
    provider = NotebookLMProvider(
        client=client,  # type: ignore[arg-type]
        notebook_map={"EU-CSRD-ESRS": "7bbf7d0b-db30-488e-8d2d-e7cbad3dbbe5"},
    )
    req = ResearchRequest(
        question="What are ESRS E1-1 obligations?",
        corpus_key="EU-CSRD-ESRS",
        mode="qa",
    )

    response = provider.query(req)

    assert [call[0] for call in client.calls] == [
        "navigate_to_notebook",
        "chat_with_notebook",
    ]
    assert response.provider == "notebooklm"
    assert response.answer_markdown == "Answer body."
    assert len(response.citations) == 1
    assert response.citations[0].source_title == "ESRS 1"


def test_provider_raises_when_corpus_mapping_missing() -> None:
    client = _FakeMCPClient()
    provider = NotebookLMProvider(client=client, notebook_map={})  # type: ignore[arg-type]
    req = ResearchRequest(question="Q", corpus_key="missing", mode="qa")
    with pytest.raises(NotebookLMMissingNotebookMappingError):
        provider.query(req)


def test_default_notebook_mapping_contains_rollout_notebook() -> None:
    settings = Settings()
    mapping = parse_notebook_map(settings.notebooklm_notebook_map_json)
    assert mapping["EU-CSRD-ESRS"] == "7bbf7d0b-db30-488e-8d2d-e7cbad3dbbe5"
