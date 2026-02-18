"""Deterministic hybrid retrieval service."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.db.models import Chunk, Embedding

LEXICAL_WEIGHT = 0.6
VECTOR_WEIGHT = 0.4


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    document_id: int
    page_number: int
    start_offset: int
    end_offset: int
    text: str
    lexical_score: float
    vector_score: float
    combined_score: float


def _tokenize(query: str) -> list[str]:
    return [token for token in query.lower().split() if token]


def _lexical_score(query_terms: list[str], text: str) -> float:
    if not query_terms:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for term in query_terms if term in text_lower)
    return hits / len(query_terms)


def _parse_embedding(payload: str) -> list[float] | None:
    try:
        values = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(values, list):
        return None
    parsed: list[float] = []
    for item in values:
        if isinstance(item, int | float):
            parsed.append(float(item))
        else:
            return None
    return parsed


def _cosine_similarity(lhs: list[float], rhs: list[float]) -> float:
    if len(lhs) != len(rhs) or len(lhs) == 0:
        return 0.0
    dot = sum(a * b for a, b in zip(lhs, rhs, strict=True))
    lhs_norm = math.sqrt(sum(a * a for a in lhs))
    rhs_norm = math.sqrt(sum(b * b for b in rhs))
    if lhs_norm == 0.0 or rhs_norm == 0.0:
        return 0.0
    return dot / (lhs_norm * rhs_norm)


def retrieve_chunks(
    db: Session,
    *,
    query: str,
    query_embedding: list[float] | None,
    top_k: int,
    document_id: int | None = None,
    model_name: str = "default",
) -> list[RetrievalResult]:
    """Run deterministic hybrid retrieval with explicit tie-breaks."""
    if top_k <= 0:
        return []

    stmt = select(Chunk).order_by(Chunk.chunk_id)
    if document_id is not None:
        stmt = stmt.where(Chunk.document_id == document_id)

    chunks = db.scalars(stmt).all()
    query_terms = _tokenize(query)

    embedding_rows = db.scalars(select(Embedding).where(Embedding.model_name == model_name)).all()
    embeddings_by_chunk_id = {row.chunk_id: row.embedding for row in embedding_rows}

    scored: list[RetrievalResult] = []
    for chunk in chunks:
        lexical_score = _lexical_score(query_terms, chunk.text)

        vector_score = 0.0
        if query_embedding is not None and chunk.id in embeddings_by_chunk_id:
            chunk_embedding = _parse_embedding(embeddings_by_chunk_id[chunk.id])
            if chunk_embedding is not None:
                vector_score = _cosine_similarity(query_embedding, chunk_embedding)

        combined_score = (LEXICAL_WEIGHT * lexical_score) + (VECTOR_WEIGHT * vector_score)

        scored.append(
            RetrievalResult(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                page_number=chunk.page_number,
                start_offset=chunk.start_offset,
                end_offset=chunk.end_offset,
                text=chunk.text,
                lexical_score=round(lexical_score, 8),
                vector_score=round(vector_score, 8),
                combined_score=round(combined_score, 8),
            )
        )

    scored.sort(key=lambda item: (-item.combined_score, item.chunk_id))
    return scored[:top_k]
