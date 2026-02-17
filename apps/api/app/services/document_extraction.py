"""Deterministic page-level extraction for uploaded documents."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from pypdf import PdfReader
from sqlalchemy import delete
from sqlalchemy.orm import Session

from apps.api.app.db.models import DocumentPage


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str
    char_count: int
    parser_version: str


def _extract_pdf_pages(content: bytes) -> list[ExtractedPage]:
    reader = PdfReader(BytesIO(content))
    pages: list[ExtractedPage] = []
    for idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(
            ExtractedPage(
                page_number=idx,
                text=text,
                char_count=len(text),
                parser_version="pdf-pypdf-v1",
            )
        )
    return pages


def _extract_docx_pages(content: bytes) -> list[ExtractedPage]:
    with ZipFile(BytesIO(content)) as archive:
        xml_bytes = archive.read("word/document.xml")

    root = ET.fromstring(xml_bytes)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []

    for para in root.findall(".//w:p", namespace):
        fragments = [node.text for node in para.findall(".//w:t", namespace) if node.text]
        if fragments:
            paragraphs.append("".join(fragments))

    text = "\n".join(paragraphs)
    return [
        ExtractedPage(
            page_number=1,
            text=text,
            char_count=len(text),
            parser_version="docx-xml-v1",
        )
    ]


def _extract_fallback_page(content: bytes) -> list[ExtractedPage]:
    text = content.decode("utf-8", errors="ignore")
    return [
        ExtractedPage(
            page_number=1,
            text=text,
            char_count=len(text),
            parser_version="raw-bytes-v1",
        )
    ]


def extract_pages_for_document(content: bytes, filename: str) -> list[ExtractedPage]:
    """Extract deterministic page records from PDF/DOCX with safe fallback."""
    extension = Path(filename).suffix.lower()

    try:
        if extension == ".pdf":
            return _extract_pdf_pages(content)
        if extension == ".docx":
            return _extract_docx_pages(content)
    except Exception:
        return _extract_fallback_page(content)

    return _extract_fallback_page(content)


def persist_document_pages(db: Session, document_id: int, pages: list[ExtractedPage]) -> None:
    """Persist extracted pages deterministically for a document."""
    db.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))

    for page in pages:
        db.add(
            DocumentPage(
                document_id=document_id,
                page_number=page.page_number,
                text=page.text,
                char_count=page.char_count,
                parser_version=page.parser_version,
            )
        )
