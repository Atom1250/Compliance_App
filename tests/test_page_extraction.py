from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from pypdf import PdfWriter
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import Company, Document, DocumentPage
from apps.api.app.services.document_extraction import (
    extract_pages_for_document,
    persist_document_pages,
)


def _prepare_db_with_document(tmp_path: Path) -> tuple[str, int]:
    db_path = tmp_path / "pages.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    with Session(engine) as session:
        company = Company(name="Page Test Co")
        session.add(company)
        session.flush()
        document = Document(company_id=company.id, title="Sample")
        session.add(document)
        session.commit()
        return db_url, document.id


def _build_fixed_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _build_fixed_docx_bytes() -> bytes:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        "<w:p><w:r><w:t>Line A</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Line B</w:t></w:r></w:p>"
        "</w:body>"
        "</w:document>"
    )

    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        "<Default Extension=\"rels\" "
        "ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )

    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )

    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def test_pdf_extraction_persists_deterministic_pages(tmp_path: Path) -> None:
    db_url, document_id = _prepare_db_with_document(tmp_path)
    pdf_bytes = _build_fixed_pdf_bytes()

    first_pages = extract_pages_for_document(pdf_bytes, "sample.pdf")
    second_pages = extract_pages_for_document(pdf_bytes, "sample.pdf")
    assert first_pages == second_pages

    engine = create_engine(db_url)
    with Session(engine) as session:
        persist_document_pages(session, document_id, first_pages)
        session.commit()
        first_rows = session.scalars(
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number)
        ).all()

        persist_document_pages(session, document_id, second_pages)
        session.commit()
        second_rows = session.scalars(
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number)
        ).all()

    first_snapshot = [
        (row.page_number, row.text, row.char_count, row.parser_version) for row in first_rows
    ]
    second_snapshot = [
        (row.page_number, row.text, row.char_count, row.parser_version) for row in second_rows
    ]

    assert first_snapshot == second_snapshot
    assert len(first_snapshot) == 2


def test_docx_basic_extraction() -> None:
    docx_bytes = _build_fixed_docx_bytes()

    pages = extract_pages_for_document(docx_bytes, "sample.docx")

    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert pages[0].text == "Line A\nLine B"
    assert pages[0].char_count == len("Line A\nLine B")
    assert pages[0].parser_version == "docx-xml-v1"


def test_fallback_extraction_strips_nul_bytes() -> None:
    content = b"abc\x00def"
    pages = extract_pages_for_document(content, "sample.bin")
    assert len(pages) == 1
    assert pages[0].text == "abcdef"
    assert pages[0].char_count == len("abcdef")
    assert pages[0].parser_version == "raw-bytes-v1"
