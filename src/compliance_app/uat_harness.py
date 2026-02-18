"""Deterministic UAT harness for end-to-end workflow validation."""

from __future__ import annotations

import json
import os
import shutil
import time
import zipfile
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
from apps.api.app.main import create_app
from compliance_app.golden_run import generate_golden_snapshot

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
        import_bundle(session, load_bundle(Path("requirements/esrs_mini_legacy/bundle.json")))
        session.commit()


def _wait_for_terminal_status(
    client: TestClient, *, run_id: int, timeout_seconds: float = 5.0
) -> str:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        response = client.get(f"/runs/{run_id}/status", headers=AUTH_HEADERS)
        if response.status_code != 200:
            raise AssertionError(f"status polling failed: {response.status_code} {response.text}")
        status = response.json()["status"]
        if status in {"completed", "failed"}:
            return status
        time.sleep(0.05)
    raise AssertionError("run did not reach terminal status in time")


def run_uat_harness(*, work_dir: Path) -> dict[str, object]:
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    db_path = work_dir / "uat.sqlite"
    object_store_root = work_dir / "object_store"
    evidence_root = work_dir / "evidence_packs"
    fixture_path = Path("tests/fixtures/golden/sample_report.txt")
    fixture_text = fixture_path.read_text()

    with _temporary_env(
        {
            "COMPLIANCE_APP_DATABASE_URL": f"sqlite:///{db_path}",
            "COMPLIANCE_APP_OBJECT_STORAGE_ROOT": str(object_store_root),
            "COMPLIANCE_APP_EVIDENCE_PACK_OUTPUT_ROOT": str(evidence_root),
            "COMPLIANCE_APP_SECURITY_ENABLED": "true",
            "COMPLIANCE_APP_AUTH_API_KEYS": "dev-key",
            "COMPLIANCE_APP_AUTH_TENANT_KEYS": "default:dev-key",
            "COMPLIANCE_APP_REQUEST_RATE_LIMIT_ENABLED": "false",
        }
    ):
        db_url = f"sqlite:///{db_path}"
        _prepare_db(db_url)
        _seed_requirements_bundle(db_url)
        app = create_app()
        client = TestClient(app)

        company = client.post(
            "/companies",
            json={
                "name": "UAT Co",
                "employees": 500,
                "turnover": 50000000.0,
                "listed_status": True,
                "reporting_year": 2026,
            },
            headers=AUTH_HEADERS,
        )
        assert company.status_code == 200, company.text
        company_id = company.json()["id"]

        upload = client.post(
            "/documents/upload",
            data={"company_id": str(company_id), "title": "Sample Report"},
            files={"file": ("sample_report.txt", fixture_text.encode(), "text/plain")},
            headers=AUTH_HEADERS,
        )
        assert upload.status_code == 200, upload.text

        run_create = client.post("/runs", json={"company_id": company_id}, headers=AUTH_HEADERS)
        assert run_create.status_code == 200, run_create.text
        run_id = run_create.json()["run_id"]

        execute = client.post(
            f"/runs/{run_id}/execute",
            json={"bundle_id": "esrs_mini", "bundle_version": "2026.01"},
            headers=AUTH_HEADERS,
        )
        assert execute.status_code == 200, execute.text
        status = _wait_for_terminal_status(client, run_id=run_id)
        if status != "completed":
            raise AssertionError(f"run failed during UAT flow: {status}")

        report = client.get(f"/runs/{run_id}/report", headers=AUTH_HEADERS)
        assert report.status_code == 200, report.text

        manifest = client.get(f"/runs/{run_id}/manifest", headers=AUTH_HEADERS)
        assert manifest.status_code == 200, manifest.text
        manifest_payload = manifest.json()

        evidence_a = client.get(f"/runs/{run_id}/evidence-pack", headers=AUTH_HEADERS)
        evidence_b = client.get(f"/runs/{run_id}/evidence-pack", headers=AUTH_HEADERS)
        assert evidence_a.status_code == 200, evidence_a.text
        assert evidence_b.status_code == 200, evidence_b.text
        if evidence_a.content != evidence_b.content:
            raise AssertionError(
                "evidence pack bytes were not deterministic across repeated requests"
            )

        zip_path = work_dir / "evidence-pack.zip"
        zip_path.write_bytes(evidence_a.content)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zip_entries = zf.namelist()
            evidence_manifest = json.loads(zf.read("manifest.json"))

        golden_snapshot = generate_golden_snapshot(document_text=fixture_text)
        golden_expected = json.loads(Path("tests/golden/golden_run_snapshot.json").read_text())
        if golden_snapshot != golden_expected:
            raise AssertionError("golden snapshot drift detected during UAT harness")

        return {
            "flow": {
                "terminal_status": status,
                "report_path_template": "/runs/{run_id}/report",
                "report_url_matches_template": report.request.url.path == f"/runs/{run_id}/report",
                "report_is_html": report.headers.get("content-type", "").startswith("text/html"),
            },
            "manifest": {
                "bundle_id": manifest_payload["bundle_id"],
                "bundle_version": manifest_payload["bundle_version"],
                "model_name": manifest_payload["model_name"],
                "retrieval_policy_version": manifest_payload["retrieval_params"][
                    "retrieval_policy"
                ]["version"],
                "retrieval_top_k": manifest_payload["retrieval_params"]["top_k"],
            },
            "evidence_pack": {
                "entries": zip_entries,
                "manifest_file_count": len(evidence_manifest["pack_files"]),
            },
            "golden_contract_hash": golden_snapshot["run_hash"],
        }
