"""Parse NotebookLM markdown responses into answer and citations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from apps.api.app.services.regulatory_research.types import Citation

_CITATIONS_HEADER: Final[str] = "CITATIONS:"


@dataclass(frozen=True)
class ParsedNotebookLMResponse:
    answer_markdown: str
    citations: list[Citation]


def parse_notebooklm_response(content: str) -> ParsedNotebookLMResponse:
    marker_index = content.upper().rfind(_CITATIONS_HEADER)
    if marker_index < 0:
        return ParsedNotebookLMResponse(answer_markdown=content.strip(), citations=[])

    answer = content[:marker_index].rstrip()
    citations_block = content[marker_index + len(_CITATIONS_HEADER) :].strip()
    citations = _parse_citations_block(citations_block)
    return ParsedNotebookLMResponse(answer_markdown=answer, citations=citations)


def _parse_citations_block(block: str) -> list[Citation]:
    citations: list[Citation] = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or not line.startswith(("-", "*")):
            continue
        item = line[1:].strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split("|")]
        if not parts or not parts[0]:
            continue
        source_title = parts[0]
        locator = parts[1] if len(parts) > 1 and parts[1] else None
        maybe_url = parts[2] if len(parts) > 2 else None
        has_url = bool(maybe_url and maybe_url.lower().startswith(("http://", "https://")))
        url = maybe_url if has_url else None
        quote = parts[3] if len(parts) > 3 and parts[3] else None
        if quote is None and maybe_url and url is None:
            quote = maybe_url
        citations.append(
            Citation(
                source_title=source_title,
                locator=locator,
                url=url,
                quote=quote,
            )
        )
    return citations
