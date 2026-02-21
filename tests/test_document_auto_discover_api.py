from pathlib import Path

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.api.routers import documents as documents_router
from apps.api.app.core.config import get_settings
from apps.api.app.db.models import Company, Document, DocumentDiscoveryCandidate
from apps.api.app.services.tavily_discovery import DownloadedDocument, TavilyCandidate
from apps.api.main import app

AUTH_HEADERS = {"X-API-Key": "dev-key", "X-Tenant-ID": "default"}


def _prepare_database(tmp_path: Path) -> tuple[str, int]:
    db_path = tmp_path / "auto_discover.sqlite"
    db_url = f"sqlite:///{db_path}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    with Session(engine) as session:
        company = Company(name="Auto Discover Co", reporting_year=2025)
        session.add(company)
        session.commit()
        company_id = company.id

    return db_url, company_id


def test_auto_discover_ingests_documents(monkeypatch, tmp_path: Path) -> None:
    db_url, company_id = _prepare_database(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    monkeypatch.setenv("COMPLIANCE_APP_OBJECT_STORAGE_ROOT", str(tmp_path / "object_store"))
    monkeypatch.setenv("COMPLIANCE_APP_TAVILY_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCE_APP_TAVILY_API_KEY", "test-key")
    get_settings.cache_clear()

    monkeypatch.setattr(
        documents_router,
        "search_tavily_documents",
        lambda **_: [
            TavilyCandidate(
                title="Sustainability Report 2025",
                url="https://example.com/a.pdf",
                score=0.9,
            ),
            TavilyCandidate(title="ESG Data Book", url="https://example.com/b.pdf", score=0.8),
        ],
    )
    monkeypatch.setattr(
        documents_router,
        "download_discovery_candidate",
        lambda **_: DownloadedDocument(
            content=b"mock report bytes",
            filename="auto-report.pdf",
            title="Sustainability Report 2025",
            source_url="https://example.com/a.pdf",
        ),
    )

    client = TestClient(app)
    response = client.post(
        "/documents/auto-discover",
        json={"company_id": company_id, "max_documents": 1},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ingested_count"] == 1
    assert payload["candidates_considered"] == 2
    assert payload["raw_candidates"] == 2
    assert payload["ingested_documents"][0]["source_url"] == "https://example.com/a.pdf"

    engine = create_engine(db_url)
    with Session(engine) as session:
        document_count = session.scalar(select(func.count(Document.id)))
        decision_rows = session.scalars(
            select(DocumentDiscoveryCandidate).order_by(DocumentDiscoveryCandidate.id)
        ).all()
    assert document_count == 1
    assert len(decision_rows) == 2
    assert [row.accepted for row in decision_rows] == [True, False]
    assert decision_rows[0].reason == "ingested"
    assert decision_rows[1].reason == "max_documents_reached"


def test_auto_discover_requires_enabled_tavily(monkeypatch, tmp_path: Path) -> None:
    db_url, company_id = _prepare_database(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    monkeypatch.setenv("COMPLIANCE_APP_TAVILY_ENABLED", "false")
    monkeypatch.setenv("COMPLIANCE_APP_TAVILY_API_KEY", "")
    get_settings.cache_clear()

    client = TestClient(app)
    response = client.post(
        "/documents/auto-discover",
        json={"company_id": company_id, "max_documents": 1},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "tavily discovery is disabled"


def test_auto_discover_persists_download_validation_rejection_reason(
    monkeypatch, tmp_path: Path
) -> None:
    db_url, company_id = _prepare_database(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    monkeypatch.setenv("COMPLIANCE_APP_OBJECT_STORAGE_ROOT", str(tmp_path / "object_store"))
    monkeypatch.setenv("COMPLIANCE_APP_TAVILY_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCE_APP_TAVILY_API_KEY", "test-key")
    get_settings.cache_clear()

    monkeypatch.setattr(
        documents_router,
        "search_tavily_documents",
        lambda **_: [
            TavilyCandidate(title="Listing", url="https://example.com/listing", score=0.95),
            TavilyCandidate(title="Report", url="https://example.com/report.pdf", score=0.9),
        ],
    )
    monkeypatch.setattr(
        documents_router,
        "download_discovery_candidate",
        lambda **_: DownloadedDocument(
            content=b"%PDF-1.7 mock",
            filename="report.pdf",
            title="Report",
            source_url="https://example.com/report.pdf",
        ),
    )

    client = TestClient(app)
    response = client.post(
        "/documents/auto-discover",
        json={"company_id": company_id, "max_documents": 2},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ingested_count"] == 1
    assert any(
        item["reason"] == "non_pdf_candidate_url"
        for item in payload["skipped"]
    )

    engine = create_engine(db_url)
    with Session(engine) as session:
        decisions = session.scalars(
            select(DocumentDiscoveryCandidate).order_by(DocumentDiscoveryCandidate.id)
        ).all()
    assert [row.reason for row in decisions] == [
        "non_pdf_candidate_url",
        "ingested",
    ]


def test_auto_discover_handles_binary_nul_content_without_request_crash(
    monkeypatch, tmp_path: Path
) -> None:
    db_url, company_id = _prepare_database(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    monkeypatch.setenv("COMPLIANCE_APP_OBJECT_STORAGE_ROOT", str(tmp_path / "object_store"))
    monkeypatch.setenv("COMPLIANCE_APP_TAVILY_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCE_APP_TAVILY_API_KEY", "test-key")
    get_settings.cache_clear()

    monkeypatch.setattr(
        documents_router,
        "search_tavily_documents",
        lambda **_: [
            TavilyCandidate(title="Binary PDF", url="https://example.com/binary.pdf", score=0.95)
        ],
    )
    monkeypatch.setattr(
        documents_router,
        "download_discovery_candidate",
        lambda **_: DownloadedDocument(
            # Invalid PDF-like bytes containing NUL should be sanitized by fallback extraction.
            content=b"%PDF-1.7\\x00binary",
            filename="binary.pdf",
            title="Binary PDF",
            source_url="https://example.com/binary.pdf",
        ),
    )

    client = TestClient(app)
    response = client.post(
        "/documents/auto-discover",
        json={"company_id": company_id, "max_documents": 1},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ingested_count"] == 1


def test_auto_discover_returns_502_when_search_provider_fails(
    monkeypatch, tmp_path: Path
) -> None:
    db_url, company_id = _prepare_database(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    monkeypatch.setenv("COMPLIANCE_APP_TAVILY_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCE_APP_TAVILY_API_KEY", "test-key")
    get_settings.cache_clear()

    def _raise_search_error(**_: object) -> list[TavilyCandidate]:
        raise RuntimeError("search backend timeout")

    monkeypatch.setattr(documents_router, "search_tavily_documents", _raise_search_error)

    client = TestClient(app)
    response = client.post(
        "/documents/auto-discover",
        json={"company_id": company_id, "max_documents": 1},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert "tavily discovery failed" in response.json()["detail"]
