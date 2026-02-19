"""Deterministic helpers for company-to-document resolution."""

from __future__ import annotations

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import Session

from apps.api.app.db.models import CompanyDocumentLink, Document, DocumentFile


def ensure_company_document_link(
    db: Session,
    *,
    company_id: int,
    document_id: int,
    tenant_id: str,
) -> None:
    existing = db.scalar(
        select(CompanyDocumentLink.id).where(
            CompanyDocumentLink.company_id == company_id,
            CompanyDocumentLink.document_id == document_id,
            CompanyDocumentLink.tenant_id == tenant_id,
        )
    )
    if existing is not None:
        return
    db.add(
        CompanyDocumentLink(
            company_id=company_id,
            document_id=document_id,
            tenant_id=tenant_id,
        )
    )


def company_document_scope_clause(*, company_id: int, tenant_id: str):
    linked_exists = exists(
        select(CompanyDocumentLink.id).where(
            and_(
                CompanyDocumentLink.document_id == Document.id,
                CompanyDocumentLink.company_id == company_id,
                CompanyDocumentLink.tenant_id == tenant_id,
            )
        )
    )
    return and_(
        Document.tenant_id == tenant_id,
        or_(Document.company_id == company_id, linked_exists),
    )


def list_company_document_ids(db: Session, *, company_id: int, tenant_id: str) -> list[int]:
    ids = db.scalars(
        select(Document.id)
        .where(company_document_scope_clause(company_id=company_id, tenant_id=tenant_id))
        .order_by(Document.id)
    ).all()
    return list(ids)


def list_company_document_hashes(db: Session, *, company_id: int, tenant_id: str) -> list[str]:
    hashes = db.scalars(
        select(DocumentFile.sha256_hash)
        .join(Document, Document.id == DocumentFile.document_id)
        .where(company_document_scope_clause(company_id=company_id, tenant_id=tenant_id))
        .order_by(DocumentFile.sha256_hash)
    ).all()
    return sorted(set(hashes))
