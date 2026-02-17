"""Deterministic chunking and retrieval-sanity helpers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from sqlalchemy import delete
from sqlalchemy.orm import Session

from apps.api.app.db.models import Chunk, DocumentPage

DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 100


@dataclass(frozen=True)
class ChunkPayload:
    chunk_id: str
    page_number: int
    start_offset: int
    end_offset: int
    text: str


def _chunk_id(document_hash: str, page_number: int, start_offset: int, end_offset: int) -> str:
    seed = f"{document_hash}:{page_number}:{start_offset}:{end_offset}".encode()
    return hashlib.sha256(seed).hexdigest()


def build_page_chunks(
    *,
    document_hash: str,
    page_number: int,
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[ChunkPayload]:
    """Split page text deterministically into overlapping chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size")

    if text == "":
        chunk_id = _chunk_id(document_hash, page_number, 0, 0)
        return [
            ChunkPayload(
                chunk_id=chunk_id,
                page_number=page_number,
                start_offset=0,
                end_offset=0,
                text="",
            )
        ]

    chunks: list[ChunkPayload] = []
    step = chunk_size - chunk_overlap
    start = 0

    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk_text = text[start:end]
        chunks.append(
            ChunkPayload(
                chunk_id=_chunk_id(document_hash, page_number, start, end),
                page_number=page_number,
                start_offset=start,
                end_offset=end,
                text=chunk_text,
            )
        )
        if end == len(text):
            break
        start += step

    return chunks


def persist_chunks_for_document(
    db: Session,
    *,
    document_id: int,
    document_hash: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> None:
    """Persist deterministic chunks for all stored pages in a document."""
    pages = (
        db.query(DocumentPage)
        .filter(DocumentPage.document_id == document_id)
        .order_by(DocumentPage.page_number)
        .all()
    )

    db.execute(delete(Chunk).where(Chunk.document_id == document_id))

    for page in pages:
        for payload in build_page_chunks(
            document_hash=document_hash,
            page_number=page.page_number,
            text=page.text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        ):
            db.add(
                Chunk(
                    document_id=document_id,
                    page_number=payload.page_number,
                    start_offset=payload.start_offset,
                    end_offset=payload.end_offset,
                    chunk_id=payload.chunk_id,
                    text=payload.text,
                    content_tsv=payload.text,
                )
            )


def rank_chunks_for_query_sanity(
    query: str, chunks: list[ChunkPayload], top_k: int
) -> list[ChunkPayload]:
    """Minimal deterministic retrieval sanity ranking by lexical overlap + chunk_id tie-break."""
    query_terms = [term for term in query.lower().split() if term]

    def score(item: ChunkPayload) -> tuple[int, str]:
        text_lower = item.text.lower()
        lexical = sum(1 for term in query_terms if term in text_lower)
        return (lexical, item.chunk_id)

    ranked = sorted(chunks, key=lambda item: (-score(item)[0], score(item)[1]))
    return ranked[:top_k]
