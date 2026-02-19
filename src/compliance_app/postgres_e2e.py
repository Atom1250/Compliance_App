"""Postgres-gated end-to-end harness for deterministic flow validation."""

from __future__ import annotations

import os
import shutil
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.requirements.importer import import_bundle, load_bundle
from apps.api.app.core.auth import _resolve_key_maps
from apps.api.app.core.config import get_settings
from apps.api.app.db.models import Run
from apps.api.app.main import create_app

AUTH_HEADERS = {"X-API-Key": "dev-key", "X-Tenant-ID": "default"}


@contextmanager
def _temporary_env(values: dict[str, str]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in values}
    try:
        os.environ.update(values)
        get_settings.cache_clear()
        _resolve_key_maps.cache_clear()
        yield
    finally:
        for key, old_value in previous.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value
        get_settings.cache_clear()
        _resolve_key_maps.cache_clear()


def _prepare_db(db_url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")


def _seed_requirements_bundle(db_url: str) -> None:
    engine = create_engine(db_url)
    with Session(engine) as session:
        import_bundle(session, load_bundle(Path("requirements/esrs_mini/bundle.json")))
        session.commit()


def _wait_for_terminal_status(*, db_url: str, run_id: int, timeout_seconds: float = 8.0) -> str:
    engine = create_engine(db_url)
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run is None:
                raise AssertionError(f"run not found: {run_id}")
            status = run.status
        if status in {"completed", "failed"}:
            return status
        time.sleep(0.05)
    raise AssertionError("run did not reach terminal status in time")


def run_postgres_e2e(*, database_url: str, work_dir: Path) -> dict[str, object]:
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    object_store_root = work_dir / "object_store"
    evidence_root = work_dir / "evidence_packs"
    fixture_text = Path("tests/fixtures/golden/sample_report.txt").read_text()

    with _temporary_env(
        {
            "COMPLIANCE_APP_DATABASE_URL": database_url,
            "COMPLIANCE_APP_OBJECT_STORAGE_ROOT": str(object_store_root),
            "COMPLIANCE_APP_EVIDENCE_PACK_OUTPUT_ROOT": str(evidence_root),
            "COMPLIANCE_APP_SECURITY_ENABLED": "true",
            "COMPLIANCE_APP_AUTH_API_KEYS": "dev-key",
            "COMPLIANCE_APP_AUTH_TENANT_KEYS": "default:dev-key",
            "COMPLIANCE_APP_REQUEST_RATE_LIMIT_ENABLED": "false",
            "COMPLIANCE_APP_OPENAI_API_KEY": "",
            "OPENAI_API_KEY": "",
        }
    ):
        _prepare_db(database_url)
        _seed_requirements_bundle(database_url)

        app = create_app()
        client = TestClient(app)

        company = client.post(
            "/companies",
            json={
                "name": "Postgres E2E Co",
                "employees": 1200,
                "turnover": 150000000.0,
                "listed_status": True,
                "reporting_year": 2026,
            },
            headers=AUTH_HEADERS,
        )
        assert company.status_code == 200, company.text
        company_id = int(company.json()["id"])

        upload = client.post(
            "/documents/upload",
            data={"company_id": str(company_id), "title": "Postgres E2E Sample"},
            files={"file": ("sample_report.txt", fixture_text.encode(), "text/plain")},
            headers=AUTH_HEADERS,
        )
        assert upload.status_code == 200, upload.text

        created_run = client.post("/runs", json={"company_id": company_id}, headers=AUTH_HEADERS)
        assert created_run.status_code == 200, created_run.text
        run_id = int(created_run.json()["run_id"])

        execute = client.post(
            f"/runs/{run_id}/execute",
            json={
                "bundle_id": "esrs_mini",
                "bundle_version": "2026.01",
                "llm_provider": "deterministic_fallback",
            },
            headers=AUTH_HEADERS,
        )
        assert execute.status_code == 200, execute.text

        terminal_status = _wait_for_terminal_status(db_url=database_url, run_id=run_id)
        assert terminal_status == "completed"

        manifest = client.get(f"/runs/{run_id}/manifest", headers=AUTH_HEADERS)
        assert manifest.status_code == 200, manifest.text
        manifest_payload = manifest.json()

        readiness = client.get(f"/runs/{run_id}/export-readiness", headers=AUTH_HEADERS)
        assert readiness.status_code == 200, readiness.text
        readiness_payload = readiness.json()

        report = client.get(f"/runs/{run_id}/report", headers=AUTH_HEADERS)
        assert report.status_code == 200, report.text

        evidence_preview = client.get(f"/runs/{run_id}/evidence-pack-preview", headers=AUTH_HEADERS)
        assert evidence_preview.status_code == 200, evidence_preview.text
        preview_payload = evidence_preview.json()

        evidence_zip = client.get(f"/runs/{run_id}/evidence-pack", headers=AUTH_HEADERS)
        assert evidence_zip.status_code == 200, evidence_zip.text

        return {
            "run_id": run_id,
            "terminal_status": terminal_status,
            "bundle_id": manifest_payload["bundle_id"],
            "bundle_version": manifest_payload["bundle_version"],
            "report_ready": readiness_payload["report_ready"],
            "evidence_pack_ready": readiness_payload["evidence_pack_ready"],
            "blocking_reasons": readiness_payload["blocking_reasons"],
            "report_status_code": report.status_code,
            "evidence_preview_status_code": evidence_preview.status_code,
            "evidence_file_count": len(preview_payload.get("pack_files", [])),
        }
