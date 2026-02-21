"""Run-level observability manifest builder."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.app.core.config import get_settings
from apps.api.app.db.models import Chunk, DocumentPage, Run, RunEvent, RunInputSnapshot


def _load_snapshot_payload(db: Session, *, run: Run) -> dict[str, Any]:
    row = db.scalar(
        select(RunInputSnapshot).where(
            RunInputSnapshot.run_id == run.id,
            RunInputSnapshot.tenant_id == run.tenant_id,
        )
    )
    if row is None:
        return {}
    try:
        payload = json.loads(row.payload_json)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_smoke_test_payload(db: Session, *, run: Run) -> dict[str, Any] | None:
    row = db.scalar(
        select(RunEvent)
        .where(
            RunEvent.run_id == run.id,
            RunEvent.tenant_id == run.tenant_id,
            RunEvent.event_type == "run.execution.retrieval_smoke_test",
        )
        .order_by(RunEvent.id.desc())
    )
    if row is None:
        return None
    payload = json.loads(row.payload)
    return payload if isinstance(payload, dict) else None


def build_run_observability_manifest(db: Session, *, run: Run) -> dict[str, Any]:
    settings = get_settings()
    snapshot = _load_snapshot_payload(db, run=run)
    selected_docs = snapshot.get("selected_documents")
    if not isinstance(selected_docs, list):
        selected_docs = []
    discovery_candidates = snapshot.get("discovery_candidates")
    if not isinstance(discovery_candidates, list):
        discovery_candidates = []

    ingest_results: list[dict[str, Any]] = []
    chunking_docs: list[dict[str, Any]] = []
    total_chunks = 0
    total_chunk_chars = 0
    text_threshold = max(1.0, float(settings.ingestion_text_char_per_page_threshold))

    for item in selected_docs:
        if not isinstance(item, dict):
            continue
        document_id = int(item.get("document_id") or 0)
        if document_id <= 0:
            continue
        page_count = int(
            db.scalar(
                select(func.count())
                .select_from(DocumentPage)
                .where(DocumentPage.document_id == document_id)
            )
            or 0
        )
        extracted_chars = int(
            db.scalar(
                select(func.coalesce(func.sum(DocumentPage.char_count), 0)).where(
                    DocumentPage.document_id == document_id
                )
            )
            or 0
        )
        avg_chars_page = round((extracted_chars / page_count), 2) if page_count else 0.0
        parse_warnings: list[str] = []
        if page_count > 0 and avg_chars_page < text_threshold:
            parse_warnings.append("LOW_EXTRACTED_TEXT_DENSITY")
        ingest_results.append(
            {
                "document_id": document_id,
                "page_count": page_count,
                "extracted_text_char_count": extracted_chars,
                "text_char_per_page": avg_chars_page,
                "ocr_used": False,
                "parse_warnings": parse_warnings,
            }
        )

        doc_chunk_count = int(
            db.scalar(
                select(func.count())
                .select_from(Chunk)
                .where(Chunk.document_id == document_id)
            )
            or 0
        )
        doc_total_chunk_chars = int(
            db.scalar(
                select(func.coalesce(func.sum(func.length(Chunk.text)), 0)).where(
                    Chunk.document_id == document_id
                )
            )
            or 0
        )
        total_chunks += doc_chunk_count
        total_chunk_chars += doc_total_chunk_chars
        avg_chunk_length = (
            round((doc_total_chunk_chars / doc_chunk_count), 2) if doc_chunk_count else 0.0
        )
        chunking_docs.append(
            {
                "document_id": document_id,
                "chunk_count": doc_chunk_count,
                "avg_chunk_length": avg_chunk_length,
            }
        )

    smoke_payload = _load_smoke_test_payload(db, run=run)
    if smoke_payload is None:
        snapshot_smoke = snapshot.get("retrieval_smoke_test")
        smoke_payload = snapshot_smoke if isinstance(snapshot_smoke, dict) else None

    return {
        "run_id": run.id,
        "terminal_status": run.status,
        "discovery_candidates": discovery_candidates,
        "selected_documents": selected_docs,
        "ingest_results": sorted(ingest_results, key=lambda row: int(row["document_id"])),
        "chunking_results": {
            "chunk_count": total_chunks,
            "avg_chunk_length": (
                round((total_chunk_chars / total_chunks), 2) if total_chunks else 0.0
            ),
            "documents": sorted(chunking_docs, key=lambda row: int(row["document_id"])),
        },
        "indexing_results": {
            "index_namespace": f"tenant:{run.tenant_id}:company:{run.company_id}",
            "status": "ready" if total_chunks > 0 else "empty",
        },
        "retrieval_smoke_test": smoke_payload,
    }
