import hashlib
import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import Chunk, Company, DatapointAssessment, Document, DocumentFile, Run
from apps.api.main import app

AUTH_DEFAULT = {"X-API-Key": "dev-key", "X-Tenant-ID": "default"}
AUTH_OTHER = {"X-API-Key": "dev-key", "X-Tenant-ID": "other"}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _prepare_fixture(tmp_path: Path, *, status: str = "completed") -> tuple[str, int, str]:
    db_path = tmp_path / "evidence_pack_api.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    with Session(engine) as session:
        company = Company(name="Evidence API Co", tenant_id="default")
        session.add(company)
        session.flush()

        run = Run(company_id=company.id, tenant_id="default", status=status)
        session.add(run)
        session.flush()

        document = Document(company_id=company.id, tenant_id="default", title="Report")
        session.add(document)
        session.flush()

        doc_bytes = b"evidence-pack-api-source"
        doc_hash = _sha256(doc_bytes)
        doc_path = tmp_path / f"{doc_hash}.bin"
        doc_path.write_bytes(doc_bytes)
        session.add(
            DocumentFile(
                document_id=document.id,
                sha256_hash=doc_hash,
                storage_uri=f"file://{doc_path}",
            )
        )
        session.flush()

        session.add(
            Chunk(
                document_id=document.id,
                chunk_id="chunk-api-1",
                page_number=1,
                start_offset=0,
                end_offset=20,
                text="Scope emissions data appears in this section.",
                content_tsv="scope emissions data",
            )
        )
        session.flush()
        session.add(
            DatapointAssessment(
                run_id=run.id,
                datapoint_key="ESRS-E1-6",
                status="Present",
                value="42",
                evidence_chunk_ids='["chunk-api-1"]',
                rationale="Evidence present.",
                model_name="deterministic-local-v1",
                prompt_hash="a" * 64,
                retrieval_params='{"query_mode":"hybrid","top_k":5}',
            )
        )
        session.commit()
        return db_url, run.id, doc_hash


def test_evidence_pack_endpoint_returns_deterministic_zip(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id, doc_hash = _prepare_fixture(tmp_path, status="completed")
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    monkeypatch.setenv("COMPLIANCE_APP_EVIDENCE_PACK_OUTPUT_ROOT", str(tmp_path / "packs"))

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    response = client.get(f"/runs/{run_id}/evidence-pack", headers=AUTH_DEFAULT)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    zip_path = tmp_path / "response.zip"
    zip_path.write_bytes(response.content)
    with zipfile.ZipFile(zip_path, "r") as zf:
        assert zf.namelist() == [
            "assessments.jsonl",
            f"documents/{doc_hash}.bin",
            "evidence.jsonl",
            "manifest.json",
        ]
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["run_id"] == run_id


def test_evidence_pack_endpoint_is_tenant_scoped(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id, _ = _prepare_fixture(tmp_path, status="completed")
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    monkeypatch.setenv("COMPLIANCE_APP_EVIDENCE_PACK_OUTPUT_ROOT", str(tmp_path / "packs"))

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    response = client.get(f"/runs/{run_id}/evidence-pack", headers=AUTH_OTHER)
    assert response.status_code == 404

    preview_response = client.get(f"/runs/{run_id}/evidence-pack-preview", headers=AUTH_OTHER)
    assert preview_response.status_code == 404


def test_evidence_pack_endpoint_requires_completed_run(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id, _ = _prepare_fixture(tmp_path, status="queued")
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    monkeypatch.setenv("COMPLIANCE_APP_EVIDENCE_PACK_OUTPUT_ROOT", str(tmp_path / "packs"))

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    response = client.get(f"/runs/{run_id}/evidence-pack", headers=AUTH_DEFAULT)
    assert response.status_code == 409

    preview_response = client.get(f"/runs/{run_id}/evidence-pack-preview", headers=AUTH_DEFAULT)
    assert preview_response.status_code == 409


def test_evidence_pack_preview_returns_manifest_summary(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id, doc_hash = _prepare_fixture(tmp_path, status="completed")
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    monkeypatch.setenv("COMPLIANCE_APP_EVIDENCE_PACK_OUTPUT_ROOT", str(tmp_path / "packs"))

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    response = client.get(f"/runs/{run_id}/evidence-pack-preview", headers=AUTH_DEFAULT)
    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == run_id
    assert payload["has_assessments"] is True
    assert payload["has_evidence"] is True
    assert payload["document_count"] == 1
    assert payload["pack_file_count"] == 3
    assert [item["path"] for item in payload["pack_files"]] == [
        "assessments.jsonl",
        f"documents/{doc_hash}.bin",
        "evidence.jsonl",
    ]
    assert all(len(item["sha256"]) == 64 for item in payload["pack_files"])
    assert payload["entries"] == [
        "assessments.jsonl",
        f"documents/{doc_hash}.bin",
        "evidence.jsonl",
        "manifest.json",
    ]


def test_evidence_pack_preview_pack_files_match_zip_manifest(monkeypatch, tmp_path: Path) -> None:
    db_url, run_id, _ = _prepare_fixture(tmp_path, status="completed")
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)
    monkeypatch.setenv("COMPLIANCE_APP_EVIDENCE_PACK_OUTPUT_ROOT", str(tmp_path / "packs"))

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    preview_response = client.get(f"/runs/{run_id}/evidence-pack-preview", headers=AUTH_DEFAULT)
    assert preview_response.status_code == 200
    preview_payload = preview_response.json()

    zip_response = client.get(f"/runs/{run_id}/evidence-pack", headers=AUTH_DEFAULT)
    assert zip_response.status_code == 200
    zip_path = tmp_path / "response-preview-compare.zip"
    zip_path.write_bytes(zip_response.content)
    with zipfile.ZipFile(zip_path, "r") as zf:
        manifest = json.loads(zf.read("manifest.json"))
        manifest_pack_files = sorted(manifest["pack_files"], key=lambda item: item["path"])

    assert preview_payload["pack_files"] == manifest_pack_files
