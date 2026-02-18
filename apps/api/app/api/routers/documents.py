"""Document ingestion and metadata endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.core.auth import AuthContext, require_auth_context
from apps.api.app.core.config import get_settings
from apps.api.app.db.models import Company, Document, DocumentFile
from apps.api.app.db.session import get_db_session
from apps.api.app.services.chunking import persist_chunks_for_document
from apps.api.app.services.document_extraction import (
    extract_pages_for_document,
    persist_document_pages,
)
from apps.api.app.services.object_storage import ensure_bytes_stored
from compliance_app.document_identity import sha256_bytes

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload")
async def upload_document(
    company_id: int = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    auth: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db_session),
) -> dict[str, str | int | bool]:
    """Ingest document bytes immutably with hash-based dedupe."""
    company = db.scalar(
        select(Company).where(Company.id == company_id, Company.tenant_id == auth.tenant_id)
    )
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company not found")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty file")

    content_hash = sha256_bytes(content)
    existing = db.scalar(
        select(DocumentFile)
        .join(Document, Document.id == DocumentFile.document_id)
        .where(DocumentFile.sha256_hash == content_hash, Document.tenant_id == auth.tenant_id)
    )
    if existing is not None:
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

    document = Document(company_id=company_id, tenant_id=auth.tenant_id, title=title)
    db.add(document)
    db.flush()

    document_file = DocumentFile(
        document_id=document.id,
        sha256_hash=content_hash,
        storage_uri=storage_uri,
    )
    db.add(document_file)
    extracted_pages = extract_pages_for_document(content, file.filename or "")
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


@router.get("/{document_id}")
def get_document(
    document_id: int,
    auth: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db_session),
) -> dict[str, str | int]:
    """Return document metadata and linked stored file reference."""
    document = db.scalar(
        select(Document).where(Document.id == document_id, Document.tenant_id == auth.tenant_id)
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found")

    document_file = db.scalar(select(DocumentFile).where(DocumentFile.document_id == document.id))
    if document_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document file not found")

    return {
        "document_id": document.id,
        "company_id": document.company_id,
        "title": document.title,
        "document_file_id": document_file.id,
        "sha256_hash": document_file.sha256_hash,
        "storage_uri": document_file.storage_uri,
    }
