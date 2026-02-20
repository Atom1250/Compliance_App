"""Deterministic document universe classification and inventory helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.db.models import Document
from apps.api.app.services.company_documents import company_document_scope_clause

_DOC_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"annual.*(20\d{2})", re.IGNORECASE), "Annual Report"),
    (re.compile(r"sustainability", re.IGNORECASE), "ESG"),
    (re.compile(r"transparency\s*act", re.IGNORECASE), "Transparency Act"),
    (re.compile(r"slavery", re.IGNORECASE), "Modern Slavery"),
    (re.compile(r"pillar\s?3", re.IGNORECASE), "Risk & Capital"),
    (re.compile(r"factbook", re.IGNORECASE), "Factbook"),
]

_YEAR_PATTERN = re.compile(r"(?<!\d)(20\d{2})(?!\d)")


@dataclass(frozen=True)
class DocumentClassification:
    doc_type: str
    reporting_year: int | None
    classification_confidence: Literal["deterministic", "manual"]


@dataclass(frozen=True)
class DocumentInventoryItem:
    document_id: int
    company_id: int
    title: str
    doc_type: str
    reporting_year: int | None
    source_url: str | None
    checksum: str | None
    classification_confidence: str


def classify_document(
    *,
    title: str,
    filename: str,
    source_url: str | None,
) -> DocumentClassification:
    haystack = " ".join(part for part in [title, filename, source_url or ""] if part).strip()
    doc_type = "Other"
    confidence: Literal["deterministic", "manual"] = "manual"
    for pattern, candidate in _DOC_PATTERNS:
        if pattern.search(haystack):
            doc_type = candidate
            confidence = "deterministic"
            break

    year_match = _YEAR_PATTERN.search(haystack)
    reporting_year = int(year_match.group(1)) if year_match else None
    return DocumentClassification(
        doc_type=doc_type,
        reporting_year=reporting_year,
        classification_confidence=confidence,
    )


def list_document_inventory(
    db: Session,
    *,
    company_id: int,
    tenant_id: str,
) -> list[DocumentInventoryItem]:
    rows = db.scalars(
        select(Document)
        .where(company_document_scope_clause(company_id=company_id, tenant_id=tenant_id))
        .order_by(Document.created_at, Document.id)
    ).all()
    from apps.api.app.db.models import DocumentFile

    if not rows:
        return []

    checksums = {
        row.document_id: row.sha256_hash
        for row in db.scalars(
            select(DocumentFile).where(DocumentFile.document_id.in_([item.id for item in rows]))
        ).all()
    }
    return [
        DocumentInventoryItem(
            document_id=item.id,
            company_id=item.company_id,
            title=item.title,
            doc_type=item.doc_type or "Other",
            reporting_year=item.reporting_year,
            source_url=item.source_url,
            checksum=checksums.get(item.id),
            classification_confidence=item.classification_confidence,
        )
        for item in rows
    ]
