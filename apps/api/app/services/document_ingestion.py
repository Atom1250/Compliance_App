"""Shared deterministic document ingestion helpers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.core.config import get_settings
from apps.api.app.db.models import Document, DocumentFile
from apps.api.app.services.chunking import persist_chunks_for_document
from apps.api.app.services.company_documents import ensure_company_document_link
from apps.api.app.services.document_extraction import (
    extract_pages_for_document,
    persist_document_pages,
)
from apps.api.app.services.object_storage import ensure_bytes_stored
from compliance_app.document_identity import sha256_bytes


def ingest_document_bytes(
    *,
    db: Session,
    tenant_id: str,
    company_id: int,
    title: str,
    filename: str,
    content: bytes,
) -> dict[str, str | int | bool]:
    """Ingest bytes immutably with hash dedupe and deterministic extraction/chunking."""
    content_hash = sha256_bytes(content)
    existing = db.scalar(
        select(DocumentFile)
        .join(Document, Document.id == DocumentFile.document_id)
        .where(DocumentFile.sha256_hash == content_hash, Document.tenant_id == tenant_id)
    )
    if existing is not None:
        ensure_company_document_link(
            db,
            company_id=company_id,
            document_id=existing.document_id,
            tenant_id=tenant_id,
        )
        db.commit()
        return {
            "document_id": existing.document_id,
            "document_file_id": existing.id,
            "sha256_hash": existing.sha256_hash,
            "storage_uri": existing.storage_uri,
            "duplicate": True,
        }

    settings = get_settings()
    stored_path = ensure_bytes_stored(settings.object_storage_root, content_hash, content)
    storage_uri = f"{settings.object_storage_uri_prefix}{stored_path.resolve()}"

    document = Document(company_id=company_id, tenant_id=tenant_id, title=title)
    db.add(document)
    db.flush()
    ensure_company_document_link(
        db,
        company_id=company_id,
        document_id=document.id,
        tenant_id=tenant_id,
    )

    document_file = DocumentFile(
        document_id=document.id,
        sha256_hash=content_hash,
        storage_uri=storage_uri,
    )
    db.add(document_file)
    extracted_pages = extract_pages_for_document(content, filename)
    persist_document_pages(db, document.id, extracted_pages)
    persist_chunks_for_document(db, document_id=document.id, document_hash=content_hash)
    db.commit()
    db.refresh(document_file)

    return {
        "document_id": document.id,
        "document_file_id": document_file.id,
        "sha256_hash": document_file.sha256_hash,
        "storage_uri": document_file.storage_uri,
        "duplicate": False,
    }
