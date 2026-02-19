import hashlib
import json
import zipfile
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.regulatory.canonical import sha256_checksum
from apps.api.app.db.models import (
    Chunk,
    Company,
    DatapointAssessment,
    Document,
    DocumentFile,
    RegulatoryBundle,
    Run,
    RunManifest,
)
from apps.api.app.services.evidence_pack import export_evidence_pack


def _prepare_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "evidence_pack.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    return Session(engine, expire_on_commit=False)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_evidence_pack_zip_manifest_and_integrity_are_deterministic(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        company = Company(name="Evidence Co")
        session.add(company)
        session.flush()

        run = Run(company_id=company.id, status="queued")
        session.add(run)
        session.flush()

        document = Document(company_id=company.id, title="Report")
        session.add(document)
        session.flush()

        doc_bytes = b"example source document bytes"
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
                chunk_id="chunk-1",
                page_number=1,
                start_offset=0,
                end_offset=20,
                text="Gross Scope 1 emissions are 42 tCO2e in FY2025.",
                content_tsv="gross scope emissions 42",
            )
        )
        session.flush()

        session.add(
            DatapointAssessment(
                run_id=run.id,
                datapoint_key="ESRS-E1-6",
                status="Present",
                value="42 tCO2e FY2025",
                evidence_chunk_ids='["chunk-1"]',
                rationale="Disclosed in report.",
                model_name="gpt-5",
                prompt_hash="prompt-hash",
                retrieval_params='{"query_mode":"hybrid","top_k":3}',
            )
        )
        session.commit()

        zip_a = tmp_path / "pack-a.zip"
        zip_b = tmp_path / "pack-b.zip"
        export_evidence_pack(session, run_id=run.id, tenant_id="default", output_zip_path=zip_a)
        export_evidence_pack(session, run_id=run.id, tenant_id="default", output_zip_path=zip_b)

        assert zip_a.read_bytes() == zip_b.read_bytes()

        with zipfile.ZipFile(zip_a, "r") as zf:
            names = zf.namelist()
            assert names == [
                "assessments.jsonl",
                f"documents/{doc_hash}.bin",
                "evidence.jsonl",
                "manifest.json",
            ]

            manifest = json.loads(zf.read("manifest.json"))
            assert manifest["run_id"] == run.id
            assert manifest["documents"] == [
                {
                    "document_id": str(document.id),
                    "path": f"documents/{doc_hash}.bin",
                    "sha256_hash": doc_hash,
                }
            ]

            for file_entry in manifest["pack_files"]:
                raw = zf.read(file_entry["path"])
                assert _sha256(raw) == file_entry["sha256"]


def test_evidence_pack_includes_registry_artifacts_in_registry_mode(tmp_path: Path) -> None:
    sample_bundle_path = Path("app/regulatory/bundles/eu_csrd_sample.json")
    sample_payload = json.loads(sample_bundle_path.read_text())
    sample_checksum = sha256_checksum(sample_payload)

    with _prepare_session(tmp_path) as session:
        company = Company(name="Registry Evidence Co", reporting_year=2026)
        session.add(company)
        session.flush()

        run = Run(company_id=company.id, status="completed", compiler_mode="registry")
        session.add(run)
        session.flush()

        session.add(
            RegulatoryBundle(
                bundle_id="eu_csrd_sample",
                version="2026.01",
                jurisdiction="EU",
                regime="CSRD_ESRS",
                checksum=sample_checksum,
                payload=sample_payload,
            )
        )
        session.add(
            RunManifest(
                run_id=run.id,
                tenant_id="default",
                document_hashes="[]",
                bundle_id="eu_csrd_sample",
                bundle_version="2026.01",
                retrieval_params='{"compiler_mode":"registry"}',
                model_name="deterministic-local-v1",
                prompt_hash="p" * 64,
                git_sha="g" * 40,
            )
        )
        session.add(
            DatapointAssessment(
                run_id=run.id,
                datapoint_key="ESRS-E1-1::E1-1-narrative",
                status="Present",
                value="yes",
                evidence_chunk_ids='["chunk-1"]',
                rationale="Disclosed.",
                model_name="gpt-5",
                prompt_hash="prompt-hash",
                retrieval_params='{"query_mode":"hybrid","top_k":3}',
            )
        )
        session.commit()

        zip_path = tmp_path / "registry-pack.zip"
        export_evidence_pack(session, run_id=run.id, tenant_id="default", output_zip_path=zip_path)

        with zipfile.ZipFile(zip_path, "r") as zf:
            assert "registry/compiled_plan.json" in zf.namelist()
            assert "registry/coverage_matrix.json" in zf.namelist()
            compiled_plan = json.loads(zf.read("registry/compiled_plan.json"))
            assert compiled_plan["bundle_id"] == "eu_csrd_sample"
            assert compiled_plan["version"] == "2026.01"
            assert compiled_plan["obligations"][0]["obligation_id"] == "ESRS-E1-1"
            coverage = json.loads(zf.read("registry/coverage_matrix.json"))
            assert coverage == [
                {
                    "absent": 0,
                    "coverage_pct": 100.0,
                    "na": 0,
                    "obligation_id": "ESRS-E1-1",
                    "partial": 0,
                    "present": 1,
                    "status": "Present",
                    "total_elements": 1,
                }
            ]
