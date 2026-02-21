"""Typed contracts for regulatory research providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ResearchMode = Literal["tagging", "mapping", "qa", "draft_prd"]
ResearchProviderLabel = Literal["notebooklm", "local_rag", "stub"]


@dataclass(frozen=True)
class ResearchRequest:
    question: str
    corpus_key: str
    mode: ResearchMode
    requirement_id: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Citation:
    source_title: str
    source_id: str | None = None
    locator: str | None = None
    quote: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class ResearchResponse:
    answer_markdown: str
    citations: list[Citation]
    provider: ResearchProviderLabel
    latency_ms: int
    request_hash: str
    confidence: float | None = None
    can_persist: bool = False
