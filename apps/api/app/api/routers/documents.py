"""Document ingestion and metadata endpoints."""

from __future__ import annotations

import time

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.api.app.core.auth import AuthContext, require_auth_context
from apps.api.app.core.config import get_settings
from apps.api.app.db.models import Company, Document, DocumentDiscoveryCandidate, DocumentFile
from apps.api.app.db.session import get_db_session
from apps.api.app.services.document_ingestion import ingest_document_bytes
from apps.api.app.services.tavily_discovery import (
    download_discovery_candidate,
    is_pdf_candidate_url,
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
    raw_candidates: int
    ingested_count: int
    ingested_documents: list[AutoDiscoverItem]
    skipped: list[AutoDiscoverSkipItem]


def _summarize_discovery_error(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code if exc.response is not None else "unknown"
        return f"http_status_{code}"
    if isinstance(exc, httpx.TimeoutException):
        return "download_timeout"
    if isinstance(exc, IntegrityError):
        return "db_integrity_error"
    return f"{type(exc).__name__}: {exc}"


@router.post("/upload")
async def upload_document(
    company_id: int | None = Form(default=None),
    title: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    auth: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db_session),
) -> dict[str, str | int | bool]:
    """Ingest document bytes immutably with hash-based dedupe."""
    errors: list[dict[str, str]] = []
    if company_id is None:
        errors.append({"field": "company_id", "message": "field required"})
    if title is None or not title.strip():
        errors.append({"field": "title", "message": "field required"})
    if file is None:
        errors.append({"field": "file", "message": "field required"})
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_upload_request", "errors": errors},
        )

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
        title=title.strip(),
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

    try:
        candidates = search_tavily_documents(
            company_name=company.name,
            reporting_year=company.reporting_year_end or company.reporting_year,
            reporting_year_start=company.reporting_year_start,
            reporting_year_end=company.reporting_year_end,
            api_key=settings.tavily_api_key,
            base_url=settings.tavily_base_url,
            timeout_seconds=settings.tavily_timeout_seconds,
            max_results=settings.tavily_max_results,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"tavily discovery failed: {type(exc).__name__}: {exc}",
        ) from exc

    # Keep runtime bounded and deterministic for UI/API consumers.
    candidate_limit = max(payload.max_documents * 2, payload.max_documents)
    candidates = candidates[:candidate_limit]
    raw_candidates = len(candidates)
    ingested: list[AutoDiscoverItem] = []
    skipped: list[AutoDiscoverSkipItem] = []
    company_id = company.id

    def _record_decision(
        *,
        source_url: str,
        title: str,
        score: float,
        accepted: bool,
        reason: str,
    ) -> None:
        db.add(
            DocumentDiscoveryCandidate(
                company_id=company_id,
                tenant_id=auth.tenant_id,
                source_url=source_url,
                title=title[:255],
                score=score,
                accepted=accepted,
                reason=reason,
            )
        )

    started_at = time.monotonic()
    considered = 0
    for candidate in candidates:
        considered += 1
        if time.monotonic() - started_at > settings.tavily_discovery_budget_seconds:
            reason = "discovery_time_budget_exceeded"
            skipped.append(AutoDiscoverSkipItem(source_url=candidate.url, reason=reason))
            _record_decision(
                source_url=candidate.url,
                title=candidate.title,
                score=candidate.score,
                accepted=False,
                reason=reason,
            )
            continue
        if not is_pdf_candidate_url(candidate.url):
            reason = "non_pdf_candidate_url"
            skipped.append(AutoDiscoverSkipItem(source_url=candidate.url, reason=reason))
            _record_decision(
                source_url=candidate.url,
                title=candidate.title,
                score=candidate.score,
                accepted=False,
                reason=reason,
            )
            continue
        if len(ingested) >= payload.max_documents:
            reason = "max_documents_reached"
            skipped.append(AutoDiscoverSkipItem(source_url=candidate.url, reason=reason))
            _record_decision(
                source_url=candidate.url,
                title=candidate.title,
                score=candidate.score,
                accepted=False,
                reason=reason,
            )
            continue
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
                company_id=company_id,
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
            _record_decision(
                source_url=candidate.url,
                title=candidate.title,
                score=candidate.score,
                accepted=True,
                reason="duplicate_ingested" if bool(result["duplicate"]) else "ingested",
            )
        except Exception as exc:
            # A failed ingestion can leave the Session in rollback-only state.
            db.rollback()
            reason = _summarize_discovery_error(exc)
            skipped.append(
                AutoDiscoverSkipItem(
                    source_url=candidate.url,
                    reason=reason,
                )
            )
            _record_decision(
                source_url=candidate.url,
                title=candidate.title,
                score=candidate.score,
                accepted=False,
                reason=reason,
            )

    db.commit()

    return AutoDiscoverResponse(
        company_id=company.id,
        candidates_considered=considered,
        raw_candidates=raw_candidates,
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
