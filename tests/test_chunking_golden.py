import json
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from pypdf import PdfWriter
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import Chunk, Company, Document, DocumentPage
from apps.api.app.services.chunking import build_page_chunks, persist_chunks_for_document
from apps.api.app.services.document_extraction import extract_pages_for_document

SNAPSHOT_PATH = Path("tests/golden/chunking_parser_snapshot.json")


def _prepare_db_with_document(tmp_path: Path) -> tuple[str, int]:
    db_path = tmp_path / "chunking_golden.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    with Session(engine) as session:
        company = Company(name="Chunking Golden Co")
        session.add(company)
        session.flush()
        document = Document(company_id=company.id, title="Golden Chunking")
        session.add(document)
        session.commit()
        return db_url, document.id


def _build_fixed_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _build_fixed_docx_bytes() -> bytes:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        "<w:p><w:r><w:t>Docx line</w:t></w:r></w:p>"
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


def test_chunking_golden_snapshot_matches_expected() -> None:
    snapshot = json.loads(SNAPSHOT_PATH.read_text())
    case = snapshot["chunking_case"]
    chunks = build_page_chunks(
        document_hash=case["document_hash"],
        page_number=case["page_number"],
        text=case["text"],
        chunk_size=case["chunk_size"],
        chunk_overlap=case["chunk_overlap"],
    )
    rows = [
        {
            "chunk_id": chunk.chunk_id,
            "page_number": chunk.page_number,
            "start_offset": chunk.start_offset,
            "end_offset": chunk.end_offset,
            "text": chunk.text,
        }
        for chunk in chunks
    ]
    assert rows == case["chunks"]


def test_persisted_chunk_offsets_and_order_are_stable(tmp_path: Path) -> None:
    snapshot = json.loads(SNAPSHOT_PATH.read_text())
    case = snapshot["chunking_case"]
    db_url, document_id = _prepare_db_with_document(tmp_path)
    engine = create_engine(db_url)
    with Session(engine) as session:
        session.add(
            DocumentPage(
                document_id=document_id,
                page_number=case["page_number"],
                text=case["text"],
                char_count=len(case["text"]),
                parser_version="pdf-pypdf-v1",
            )
        )
        session.commit()

        persist_chunks_for_document(
            session,
            document_id=document_id,
            document_hash=case["document_hash"],
            chunk_size=case["chunk_size"],
            chunk_overlap=case["chunk_overlap"],
        )
        session.commit()
        first = session.scalars(
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.page_number, Chunk.start_offset, Chunk.end_offset, Chunk.chunk_id)
        ).all()

        persist_chunks_for_document(
            session,
            document_id=document_id,
            document_hash=case["document_hash"],
            chunk_size=case["chunk_size"],
            chunk_overlap=case["chunk_overlap"],
        )
        session.commit()
        second = session.scalars(
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.page_number, Chunk.start_offset, Chunk.end_offset, Chunk.chunk_id)
        ).all()

    first_rows = [
        (row.page_number, row.start_offset, row.end_offset, row.chunk_id) for row in first
    ]
    second_rows = [
        (row.page_number, row.start_offset, row.end_offset, row.chunk_id) for row in second
    ]
    assert first_rows == second_rows


def test_extraction_parser_versions_are_pinned() -> None:
    snapshot = json.loads(SNAPSHOT_PATH.read_text())
    parser_versions = snapshot["parser_versions"]

    pdf_pages = extract_pages_for_document(_build_fixed_pdf_bytes(), "sample.pdf")
    docx_pages = extract_pages_for_document(_build_fixed_docx_bytes(), "sample.docx")
    fallback_pages = extract_pages_for_document(b"plain text", "sample.txt")

    assert all(page.parser_version == parser_versions["pdf"] for page in pdf_pages)
    assert all(page.parser_version == parser_versions["docx"] for page in docx_pages)
    assert all(page.parser_version == parser_versions["fallback"] for page in fallback_pages)
