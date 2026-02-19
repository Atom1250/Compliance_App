"""Deterministic hybrid retrieval service."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.db.models import Chunk, Document, Embedding


@dataclass(frozen=True)
class RetrievalPolicy:
    version: str
    lexical_weight: float
    vector_weight: float
    tie_break: str


DEFAULT_RETRIEVAL_POLICY = RetrievalPolicy(
    version="hybrid-v1",
    lexical_weight=0.6,
    vector_weight=0.4,
    tie_break="chunk_id",
)


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


def get_retrieval_policy() -> RetrievalPolicy:
    return DEFAULT_RETRIEVAL_POLICY


def retrieval_policy_to_dict(policy: RetrievalPolicy) -> dict[str, float | str]:
    return asdict(policy)


def _tokenize(query: str) -> list[str]:
    return [token for token in query.lower().split() if token]


def _lexical_score(query_terms: list[str], text: str) -> float:
    if not query_terms:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for term in query_terms if term in text_lower)
    return hits / len(query_terms)


def _parse_embedding(payload: object) -> list[float] | None:
    if isinstance(payload, list | tuple):
        parsed: list[float] = []
        for item in payload:
            if isinstance(item, int | float):
                parsed.append(float(item))
            else:
                return None
        return parsed

    if not isinstance(payload, str):
        return None

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
    tenant_id: str | None = None,
    document_id: int | None = None,
    model_name: str = "default",
    policy: RetrievalPolicy | None = None,
) -> list[RetrievalResult]:
    """Run deterministic hybrid retrieval with explicit tie-breaks."""
    if top_k <= 0:
        return []

    active_policy = policy or get_retrieval_policy()

    stmt = select(Chunk).join(Document, Document.id == Chunk.document_id).order_by(Chunk.chunk_id)
    if tenant_id is not None:
        stmt = stmt.where(Document.tenant_id == tenant_id)
    if document_id is not None:
        stmt = stmt.where(Chunk.document_id == document_id)

    chunks = db.scalars(stmt).all()
    query_terms = _tokenize(query)

    chunk_ids = [chunk.id for chunk in chunks]
    if not chunk_ids:
        embedding_rows = []
    else:
        embedding_rows = db.scalars(
            select(Embedding).where(
                Embedding.model_name == model_name,
                Embedding.chunk_id.in_(chunk_ids),
            )
        ).all()
    embeddings_by_chunk_id = {
        row.chunk_id: (row.embedding_vector if row.embedding_vector is not None else row.embedding)
        for row in embedding_rows
    }

    scored: list[RetrievalResult] = []
    for chunk in chunks:
        lexical_score = _lexical_score(query_terms, chunk.text)

        vector_score = 0.0
        if query_embedding is not None and chunk.id in embeddings_by_chunk_id:
            chunk_embedding = _parse_embedding(embeddings_by_chunk_id[chunk.id])
            if chunk_embedding is not None:
                vector_score = _cosine_similarity(query_embedding, chunk_embedding)

        combined_score = (active_policy.lexical_weight * lexical_score) + (
            active_policy.vector_weight * vector_score
        )

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

    if active_policy.tie_break != "chunk_id":
        raise ValueError(f"Unsupported tie-break policy: {active_policy.tie_break}")
    scored.sort(key=lambda item: (-item.combined_score, item.chunk_id))
    return scored[:top_k]
