"""Deterministic hashing for research requests."""

from __future__ import annotations

import hashlib
import re

from apps.api.app.services.regulatory_research.types import ResearchRequest

_WHITESPACE = re.compile(r"\s+")


def normalize_question(text: str) -> str:
    return _WHITESPACE.sub(" ", text.strip())


def compute_request_hash(req: ResearchRequest) -> str:
    normalized_question = normalize_question(req.question)
    payload = "|".join(
        [
            normalized_question,
            req.corpus_key.strip(),
            req.mode,
            req.requirement_id.strip() if req.requirement_id else "",
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
