from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import Company, Document, DocumentFile
from apps.api.main import app

AUTH_HEADERS = {"X-API-Key": "dev-key", "X-Tenant-ID": "default"}


def _prepare_database(tmp_path: Path) -> tuple[str, int]:
    db_path = tmp_path / "document_inventory.sqlite"
    db_url = f"sqlite:///{db_path}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    with Session(engine) as session:
        company = Company(name="Inventory Co", reporting_year=2025)
        session.add(company)
        session.flush()

        doc = Document(
            company_id=company.id,
            tenant_id="default",
            title="Annual Sustainability Report 2024",
            doc_type="Annual Report",
            reporting_year=2024,
            source_url="https://example.com/report.pdf",
            classification_confidence="deterministic",
        )
        session.add(doc)
        session.flush()
        session.add(
            DocumentFile(
                document_id=doc.id,
                sha256_hash="b" * 64,
                storage_uri="file:///tmp/report.pdf",
            )
        )
        session.commit()
        return db_url, company.id


def test_document_inventory_returns_classified_rows(monkeypatch, tmp_path: Path) -> None:
    db_url, company_id = _prepare_database(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()

    client = TestClient(app)
    response = client.get(f"/documents/inventory/{company_id}", headers=AUTH_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    row = payload[0]
    assert row["doc_type"] == "Annual Report"
    assert row["reporting_year"] == 2024
    assert row["classification_confidence"] == "deterministic"
    assert row["checksum"] == "b" * 64
