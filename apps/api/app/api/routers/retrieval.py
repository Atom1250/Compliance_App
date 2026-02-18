"""Retrieval API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.app.db.session import get_db_session
from apps.api.app.services.retrieval import retrieve_chunks

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=100)
    document_id: int | None = None
    model_name: str = "default"
    query_embedding: list[float] | None = None


class RetrievalItem(BaseModel):
    chunk_id: str
    document_id: int
    page_number: int
    start_offset: int
    end_offset: int
    text: str
    lexical_score: float
    vector_score: float
    combined_score: float


class RetrievalResponse(BaseModel):
    results: list[RetrievalItem]


@router.post("/search", response_model=RetrievalResponse)
def search(payload: RetrievalRequest, db: Session = Depends(get_db_session)) -> RetrievalResponse:
    """Run deterministic hybrid retrieval and return structured results."""
    results = retrieve_chunks(
        db,
        query=payload.query,
        query_embedding=payload.query_embedding,
        top_k=payload.top_k,
        document_id=payload.document_id,
        model_name=payload.model_name,
    )

    return RetrievalResponse(results=[RetrievalItem(**item.__dict__) for item in results])
