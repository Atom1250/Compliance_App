"""Document ingestion and metadata endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.core.auth import AuthContext, require_auth_context
from apps.api.app.core.config import get_settings
from apps.api.app.db.models import Company, Document, DocumentFile
from apps.api.app.db.session import get_db_session
from apps.api.app.services.document_ingestion import ingest_document_bytes
from apps.api.app.services.tavily_discovery import (
    download_discovery_candidate,
    search_tavily_documents,
)

router = APIRouter(prefix="/documents", tags=["documents"])


class AutoDiscoverRequest(BaseModel):
    company_id: int = Field(ge=1)
    max_documents: int = Field(default=3, ge=1, le=10)


class AutoDiscoverItem(BaseModel):
    document_id: int
    title: str
    source_url: str
    duplicate: bool


class AutoDiscoverSkipItem(BaseModel):
    source_url: str
    reason: str


class AutoDiscoverResponse(BaseModel):
    company_id: int
    candidates_considered: int
    ingested_count: int
    ingested_documents: list[AutoDiscoverItem]
    skipped: list[AutoDiscoverSkipItem]


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

    return ingest_document_bytes(
        db=db,
        tenant_id=auth.tenant_id,
        company_id=company_id,
        title=title,
        filename=file.filename or "uploaded-document.bin",
        content=content,
    )


@router.post("/auto-discover", response_model=AutoDiscoverResponse)
def auto_discover_documents(
    payload: AutoDiscoverRequest,
    auth: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db_session),
) -> AutoDiscoverResponse:
    company = db.scalar(
        select(Company).where(Company.id == payload.company_id, Company.tenant_id == auth.tenant_id)
    )
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company not found")

    settings = get_settings()
    if not settings.tavily_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tavily discovery is disabled",
        )
    if not settings.tavily_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tavily api key is not configured",
        )

    candidates = search_tavily_documents(
        company_name=company.name,
        reporting_year=company.reporting_year_end or company.reporting_year,
        api_key=settings.tavily_api_key,
        base_url=settings.tavily_base_url,
        timeout_seconds=settings.tavily_timeout_seconds,
        max_results=settings.tavily_max_results,
    )
    ingested: list[AutoDiscoverItem] = []
    skipped: list[AutoDiscoverSkipItem] = []

    for candidate in candidates:
        if len(ingested) >= payload.max_documents:
            break
        try:
            downloaded = download_discovery_candidate(
                candidate=candidate,
                timeout_seconds=settings.tavily_download_timeout_seconds,
                max_document_bytes=settings.tavily_max_document_bytes,
            )
            title = downloaded.title or downloaded.filename
            result = ingest_document_bytes(
                db=db,
                tenant_id=auth.tenant_id,
                company_id=company.id,
                title=title[:255],
                filename=downloaded.filename,
                content=downloaded.content,
            )
            ingested.append(
                AutoDiscoverItem(
                    document_id=int(result["document_id"]),
                    title=title,
                    source_url=downloaded.source_url,
                    duplicate=bool(result["duplicate"]),
                )
            )
        except Exception as exc:
            skipped.append(
                AutoDiscoverSkipItem(
                    source_url=candidate.url,
                    reason=f"{type(exc).__name__}: {exc}",
                )
            )

    return AutoDiscoverResponse(
        company_id=company.id,
        candidates_considered=len(candidates),
        ingested_count=len(ingested),
        ingested_documents=ingested,
        skipped=skipped,
    )


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
