from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.core.config import get_settings
from apps.api.app.db.models import Company, Document, DocumentFile, DocumentPage
from apps.api.main import app

AUTH_HEADERS = {"X-API-Key": "dev-key", "X-Tenant-ID": "default"}


def _prepare_database(tmp_path: Path) -> tuple[str, int]:
    db_path = tmp_path / "upload.sqlite"
    db_url = f"sqlite:///{db_path}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    with Session(engine) as session:
        company = Company(name="Upload Test Co")
        session.add(company)
        session.commit()
        company_id = company.id

    return db_url, company_id


def test_upload_and_retrieval_with_hash_dedup(monkeypatch, tmp_path: Path) -> None:
    storage_root = tmp_path / "object_store"
    db_url, company_id = _prepare_database(tmp_path)

    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    monkeypatch.setenv("COMPLIANCE_APP_OBJECT_STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()

    client = TestClient(app)
    file_bytes = b"deterministic document bytes"

    first_upload = client.post(
        "/documents/upload",
        data={"company_id": str(company_id), "title": "Annual Report"},
        files={"file": ("report.pdf", file_bytes, "application/pdf")},
        headers=AUTH_HEADERS,
    )
    assert first_upload.status_code == 200
    first_payload = first_upload.json()
    assert first_payload["duplicate"] is False

    stored_uri = first_payload["storage_uri"]
    assert stored_uri.startswith("file://")
    stored_path = Path(stored_uri.removeprefix("file://"))
    assert stored_path.read_bytes() == file_bytes

    retrieved = client.get(f"/documents/{first_payload['document_id']}", headers=AUTH_HEADERS)
    assert retrieved.status_code == 200
    retrieved_payload = retrieved.json()
    assert retrieved_payload["sha256_hash"] == first_payload["sha256_hash"]
    assert retrieved_payload["storage_uri"] == first_payload["storage_uri"]

    duplicate_upload = client.post(
        "/documents/upload",
        data={"company_id": str(company_id), "title": "Annual Report Copy"},
        files={"file": ("report-copy.pdf", file_bytes, "application/pdf")},
        headers=AUTH_HEADERS,
    )
    assert duplicate_upload.status_code == 200
    duplicate_payload = duplicate_upload.json()
    assert duplicate_payload["duplicate"] is True
    assert duplicate_payload["sha256_hash"] == first_payload["sha256_hash"]
    assert duplicate_payload["storage_uri"] == first_payload["storage_uri"]
    assert duplicate_payload["document_file_id"] == first_payload["document_file_id"]
    assert duplicate_payload["document_id"] == first_payload["document_id"]

    engine = create_engine(db_url)
    with Session(engine) as session:
        document_count = session.scalar(select(func.count(Document.id)))
        document_file_count = session.scalar(select(func.count(DocumentFile.id)))
        document_page_count = session.scalar(select(func.count(DocumentPage.id)))

    assert document_count == 1
    assert document_file_count == 1
    assert document_page_count == 1
