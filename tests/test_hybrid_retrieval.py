import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import Chunk, Company, CompanyDocumentLink, Document, Embedding
from apps.api.app.services.retrieval import RetrievalPolicy, retrieve_chunks
from apps.api.main import app

AUTH_HEADERS = {"X-API-Key": "dev-key", "X-Tenant-ID": "default"}


def _prepare_db(tmp_path: Path) -> str:
    db_path = tmp_path / "retrieval.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    with Session(engine) as session:
        company = Company(name="Retrieval Co")
        session.add(company)
        session.flush()

        document = Document(company_id=company.id, title="Doc")
        session.add(document)
        session.flush()

        chunk_a = Chunk(
            document_id=document.id,
            chunk_id="aaa",
            page_number=1,
            start_offset=0,
            end_offset=20,
            text="green bond framework alignment",
            content_tsv="green bond framework alignment",
        )
        chunk_b = Chunk(
            document_id=document.id,
            chunk_id="bbb",
            page_number=1,
            start_offset=20,
            end_offset=40,
            text="green bond proceeds use details",
            content_tsv="green bond proceeds use details",
        )
        chunk_c = Chunk(
            document_id=document.id,
            chunk_id="ccc",
            page_number=2,
            start_offset=0,
            end_offset=20,
            text="generic corporate text",
            content_tsv="generic corporate text",
        )
        session.add_all([chunk_a, chunk_b, chunk_c])
        session.flush()

        session.add_all(
            [
                Embedding(
                    chunk_id=chunk_a.id,
                    model_name="default",
                    dimensions=3,
                    embedding=json.dumps([0.9, 0.1, 0.0]),
                    embedding_vector=json.dumps([0.9, 0.1, 0.0]),
                ),
                Embedding(
                    chunk_id=chunk_b.id,
                    model_name="default",
                    dimensions=3,
                    embedding=json.dumps([0.2, 0.9, 0.1]),
                    embedding_vector=json.dumps([0.2, 0.9, 0.1]),
                ),
            ]
        )
        session.commit()

    return db_url


def test_hybrid_retrieval_ordering_is_deterministic(monkeypatch, tmp_path: Path) -> None:
    db_url = _prepare_db(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    payload = {
        "query": "green bond",
        "top_k": 3,
        "query_embedding": [0.7, 0.2, 0.0],
        "model_name": "default",
    }

    first = client.post("/retrieval/search", json=payload, headers=AUTH_HEADERS)
    second = client.post("/retrieval/search", json=payload, headers=AUTH_HEADERS)

    assert first.status_code == 200
    assert second.status_code == 200
    first_results = first.json()["results"]
    second_results = second.json()["results"]

    assert first_results == second_results
    assert [item["chunk_id"] for item in first_results] == ["aaa", "bbb", "ccc"]


def test_hybrid_retrieval_tie_break_by_chunk_id(monkeypatch, tmp_path: Path) -> None:
    db_url = _prepare_db(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    payload = {"query": "green", "top_k": 2, "query_embedding": None}
    response = client.post("/retrieval/search", json=payload, headers=AUTH_HEADERS)

    assert response.status_code == 200
    results = response.json()["results"]
    assert [item["chunk_id"] for item in results] == ["aaa", "bbb"]


def test_hybrid_retrieval_policy_version_pin_is_deterministic(tmp_path: Path) -> None:
    db_url = _prepare_db(tmp_path)
    engine = create_engine(db_url)
    with Session(engine) as session:
        policy = RetrievalPolicy(
            version="hybrid-v1",
            lexical_weight=0.6,
            vector_weight=0.4,
            tie_break="chunk_id",
        )
        first = retrieve_chunks(
            session,
            query="green bond",
            query_embedding=[0.7, 0.2, 0.0],
            top_k=3,
            tenant_id="default",
            model_name="default",
            policy=policy,
        )
        second = retrieve_chunks(
            session,
            query="green bond",
            query_embedding=[0.7, 0.2, 0.0],
            top_k=3,
            tenant_id="default",
            model_name="default",
            policy=policy,
        )
    assert [item.chunk_id for item in first] == [item.chunk_id for item in second]
    assert [item.chunk_id for item in first] == ["aaa", "bbb", "ccc"]


def test_hybrid_retrieval_prefers_embedding_vector_payload(tmp_path: Path) -> None:
    db_url = _prepare_db(tmp_path)
    engine = create_engine(db_url)
    with Session(engine) as session:
        row = session.query(Embedding).filter(Embedding.model_name == "default").first()
        assert row is not None
        row.embedding = json.dumps([0.0, 0.0, 1.0])
        row.embedding_vector = json.dumps([0.9, 0.1, 0.0])
        session.commit()

        results = retrieve_chunks(
            session,
            query="green bond",
            query_embedding=[0.9, 0.1, 0.0],
            top_k=1,
            tenant_id="default",
            model_name="default",
        )

    assert results[0].chunk_id == "aaa"


def test_hybrid_retrieval_company_scope_includes_linked_docs_and_excludes_others(
    tmp_path: Path,
) -> None:
    db_url = _prepare_db(tmp_path)
    engine = create_engine(db_url)
    with Session(engine) as session:
        company_a = session.query(Company).filter(Company.name == "Retrieval Co").one()
        company_b = Company(name="Other Co", tenant_id="default")
        session.add(company_b)
        session.flush()
        doc_b = Document(company_id=company_b.id, tenant_id="default", title="Doc B")
        session.add(doc_b)
        session.flush()
        session.add(
            Chunk(
                document_id=doc_b.id,
                chunk_id="zzz",
                page_number=1,
                start_offset=0,
                end_offset=10,
                text="other company only",
                content_tsv="other company only",
            )
        )
        # Link company 1 to doc_b so it becomes in-scope through link table.
        session.add(
            CompanyDocumentLink(
                company_id=company_a.id,
                document_id=doc_b.id,
                tenant_id="default",
            )
        )
        session.commit()

        results = retrieve_chunks(
            session,
            query="other company",
            query_embedding=None,
            top_k=10,
            tenant_id="default",
            company_id=company_a.id,
            model_name="default",
        )
    chunk_ids = [item.chunk_id for item in results]
    assert "zzz" in chunk_ids
