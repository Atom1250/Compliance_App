from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import Company, CompanyDocumentLink, Document, DocumentFile
from apps.api.app.services.document_ingestion import ingest_document_bytes


def _prepare_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "company_doc_link.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    return Session(engine)


def test_duplicate_hash_links_existing_document_to_second_company(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("COMPLIANCE_APP_OBJECT_STORAGE_ROOT", str(tmp_path / "object_store"))
    with _prepare_session(tmp_path) as session:
        company_a = Company(name="A", tenant_id="default")
        company_b = Company(name="B", tenant_id="default")
        session.add_all([company_a, company_b])
        session.commit()

        payload = b"%PDF-1.7 duplicate file"
        first = ingest_document_bytes(
            db=session,
            tenant_id="default",
            company_id=company_a.id,
            title="A Report",
            filename="a.pdf",
            content=payload,
        )
        second = ingest_document_bytes(
            db=session,
            tenant_id="default",
            company_id=company_b.id,
            title="B Report",
            filename="b.pdf",
            content=payload,
        )

        assert first["document_id"] == second["document_id"]
        assert second["duplicate"] is True

        link_count = session.scalar(
            select(func.count(CompanyDocumentLink.id)).where(
                CompanyDocumentLink.document_id == int(first["document_id"])
            )
        )
        assert link_count == 2

        document_count = session.scalar(select(func.count(Document.id)))
        file_count = session.scalar(select(func.count(DocumentFile.id)))
        assert document_count == 1
        assert file_count == 1
