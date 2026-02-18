from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import Chunk, Company, Document
from apps.api.main import app


def _prepare_db(tmp_path: Path) -> tuple[str, int]:
    db_path = tmp_path / "tenant_isolation.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    with Session(engine) as session:
        company_a = Company(name="Tenant A Co", tenant_id="tenant-a")
        company_b = Company(name="Tenant B Co", tenant_id="tenant-b")
        session.add_all([company_a, company_b])
        session.flush()

        document_a = Document(company_id=company_a.id, tenant_id="tenant-a", title="Doc A")
        document_b = Document(company_id=company_b.id, tenant_id="tenant-b", title="Doc B")
        session.add_all([document_a, document_b])
        session.flush()

        session.add_all(
            [
                Chunk(
                    document_id=document_a.id,
                    chunk_id="ta-1",
                    page_number=1,
                    start_offset=0,
                    end_offset=32,
                    text="green bond framework tenant a",
                    content_tsv="green bond framework tenant a",
                ),
                Chunk(
                    document_id=document_b.id,
                    chunk_id="tb-1",
                    page_number=1,
                    start_offset=0,
                    end_offset=32,
                    text="green bond framework tenant b",
                    content_tsv="green bond framework tenant b",
                ),
            ]
        )
        session.commit()
        document_a_id = document_a.id

    return db_url, document_a_id


def test_missing_api_key_is_blocked(monkeypatch, tmp_path: Path) -> None:
    db_url, _ = _prepare_db(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    response = client.post("/retrieval/search", json={"query": "green bond", "top_k": 2})
    assert response.status_code == 401


def test_tenant_isolation_blocks_cross_tenant_document_access(monkeypatch, tmp_path: Path) -> None:
    db_url, document_a_id = _prepare_db(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    response = client.get(
        f"/documents/{document_a_id}",
        headers={"X-API-Key": "dev-key", "X-Tenant-ID": "tenant-b"},
    )
    assert response.status_code == 404


def test_retrieval_results_are_tenant_scoped(monkeypatch, tmp_path: Path) -> None:
    db_url, _ = _prepare_db(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    payload = {"query": "green bond framework", "top_k": 5, "query_embedding": None}
    response_a = client.post(
        "/retrieval/search",
        json=payload,
        headers={"X-API-Key": "dev-key", "X-Tenant-ID": "tenant-a"},
    )
    response_b = client.post(
        "/retrieval/search",
        json=payload,
        headers={"X-API-Key": "dev-key", "X-Tenant-ID": "tenant-b"},
    )

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    chunks_a = [item["chunk_id"] for item in response_a.json()["results"]]
    chunks_b = [item["chunk_id"] for item in response_b.json()["results"]]
    assert chunks_a == ["ta-1"]
    assert chunks_b == ["tb-1"]
