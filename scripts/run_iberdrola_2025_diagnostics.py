#!/usr/bin/env python3
"""Run Iberdrola 2025 diagnostics across providers and emit per-run logs."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from apps.api.app.core.auth import _resolve_key_maps
from apps.api.app.core.config import get_settings

AUTH_HEADERS = {"X-API-Key": "dev-key", "X-Tenant-ID": "default"}
DEFAULT_FALLBACK_REPORT_URL = (
    "https://www.annualreports.com/HostedData/AnnualReportArchive/i/OTC_IBDSF_2023.pdf"
)


@contextmanager
def _temporary_env(values: dict[str, str]) -> Any:
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


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, cwd=ROOT)


def _wait_for_terminal_status(client: TestClient, run_id: int, timeout_seconds: float) -> str:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        response = client.get(f"/runs/{run_id}/status", headers=AUTH_HEADERS)
        response.raise_for_status()
        status = str(response.json().get("status", "unknown"))
        if status in {"completed", "failed"}:
            return status
        time.sleep(1.0)
    return "timeout"


def _json_or_error(response) -> dict[str, Any]:
    try:
        payload: Any = response.json()
        if isinstance(payload, dict):
            return payload
        return {"_json": payload}
    except Exception:
        return {"_text": response.text}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _download_fallback_report(url: str, destination: Path) -> Path:
    import httpx

    destination.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        destination.write_bytes(response.content)
    return destination


def _execute_run(
    client: TestClient,
    *,
    company_id: int,
    provider: str,
    research_provider: str,
    bundle_id: str,
    bundle_version: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    run_create = client.post("/runs", json={"company_id": company_id}, headers=AUTH_HEADERS)
    run_create.raise_for_status()
    run_id = int(run_create.json()["run_id"])

    execute_payload = {
        "bundle_id": bundle_id,
        "bundle_version": bundle_version,
        "llm_provider": provider,
        "regulatory_research_provider": research_provider,
        "bypass_cache": True,
    }
    execute = client.post(
        f"/runs/{run_id}/execute",
        json=execute_payload,
        headers=AUTH_HEADERS,
    )
    execute.raise_for_status()

    terminal_status = _wait_for_terminal_status(client, run_id, timeout_seconds)
    endpoints: dict[str, Any] = {}
    for name, path in [
        ("status", f"/runs/{run_id}/status"),
        ("diagnostics", f"/runs/{run_id}/diagnostics"),
        ("events", f"/runs/{run_id}/events"),
        ("manifest", f"/runs/{run_id}/manifest"),
        ("export_readiness", f"/runs/{run_id}/export-readiness"),
        ("report_preview", f"/runs/{run_id}/report-preview"),
        ("report_html", f"/runs/{run_id}/report-html"),
        ("evidence_pack_preview", f"/runs/{run_id}/evidence-pack-preview"),
    ]:
        resp = client.get(path, headers=AUTH_HEADERS)
        endpoints[name] = {
            "status_code": resp.status_code,
            "payload": _json_or_error(resp),
        }

    return {
        "run_id": run_id,
        "provider": provider,
        "research_provider": research_provider,
        "execute_payload": execute_payload,
        "terminal_status": terminal_status,
        "execute_response": _json_or_error(execute),
        "endpoints": endpoints,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Iberdrola 2025 run diagnostics matrix")
    parser.add_argument("--work-dir", default="outputs/iberdrola_2025_diagnostics")
    parser.add_argument(
        "--database-url",
        default="",
        help="Optional DB URL override (recommended: Postgres URL).",
    )
    parser.add_argument("--max-documents", type=int, default=3)
    parser.add_argument("--bundle-id", default="esrs_mini")
    parser.add_argument("--bundle-version", default="2026.01")
    parser.add_argument("--timeout-seconds", type=float, default=240.0)
    args = parser.parse_args()

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    root = ROOT / args.work_dir / timestamp
    db_path = root / "iberdrola_2025.sqlite"
    object_store_root = root / "object_store"
    evidence_root = root / "evidence_packs"
    logs_root = root / "logs"
    logs_root.mkdir(parents=True, exist_ok=True)
    database_url = args.database_url.strip() or f"sqlite:///{db_path}"
    sqlite_mode = database_url.startswith("sqlite:///")

    env = {
        "COMPLIANCE_APP_DATABASE_URL": database_url,
        "COMPLIANCE_APP_OBJECT_STORAGE_ROOT": str(object_store_root),
        "COMPLIANCE_APP_EVIDENCE_PACK_OUTPUT_ROOT": str(evidence_root),
        "COMPLIANCE_APP_SECURITY_ENABLED": "true",
        "COMPLIANCE_APP_AUTH_API_KEYS": "dev-key",
        "COMPLIANCE_APP_AUTH_TENANT_KEYS": "default:dev-key",
        "COMPLIANCE_APP_REQUEST_RATE_LIMIT_ENABLED": "false",
        "COMPLIANCE_APP_TAVILY_ENABLED": "true",
    }
    if sqlite_mode:
        env["COMPLIANCE_APP_ALLOW_SQLITE_TRANSITIONAL"] = "true"

    if root.exists():
        shutil.rmtree(root)
        logs_root.mkdir(parents=True, exist_ok=True)

    with _temporary_env(env):
        _run([str(ROOT / ".venv/bin/python"), "-m", "alembic", "upgrade", "head"])
        _run(
            [
                str(ROOT / ".venv/bin/python"),
                "-m",
                "app.requirements",
                "import",
                "--bundle",
                "requirements/esrs_mini/bundle.json",
            ]
        )
        _run(
            [
                str(ROOT / ".venv/bin/python"),
                "-m",
                "app.requirements",
                "import",
                "--bundle",
                "requirements/esrs_mini_legacy/bundle.json",
            ]
        )
        _run(
            [
                str(ROOT / ".venv/bin/python"),
                "-m",
                "app.requirements",
                "import",
                "--bundle",
                "requirements/green_finance_icma_eugb/bundle.json",
            ]
        )

        from apps.api.app.main import create_app

        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)

        health = client.get("/llm-health-matrix", headers=AUTH_HEADERS)
        _write_json(
            logs_root / "llm_health_matrix.json",
            {"status_code": health.status_code, "payload": _json_or_error(health)},
        )

        company = client.post(
            "/companies",
            headers=AUTH_HEADERS,
            json={
                "name": "Iberdrola SA",
                "employees": 42000,
                "turnover": 50000000000.0,
                "listed_status": True,
                "reporting_year": 2025,
                "reporting_year_start": 2025,
                "reporting_year_end": 2025,
            },
        )
        company.raise_for_status()
        company_payload = company.json()
        company_id = int(company_payload["id"])
        _write_json(logs_root / "company.json", company_payload)

        discovery = client.post(
            "/documents/auto-discover",
            headers=AUTH_HEADERS,
            json={"company_id": company_id, "max_documents": args.max_documents},
        )
        discovery_payload = _json_or_error(discovery)
        _write_json(
            logs_root / "auto_discover.json",
            {"status_code": discovery.status_code, "payload": discovery_payload},
        )

        inventory = client.get(f"/documents/inventory/{company_id}", headers=AUTH_HEADERS)
        inventory_payload = _json_or_error(inventory)
        _write_json(
            logs_root / "document_inventory_initial.json",
            {"status_code": inventory.status_code, "payload": inventory_payload},
        )
        doc_count = len(inventory_payload.get("documents", [])) if isinstance(inventory_payload, dict) else 0
        fallback_upload_used = False
        if doc_count == 0:
            fallback_path = _download_fallback_report(
                DEFAULT_FALLBACK_REPORT_URL,
                root / "downloads" / "iberdrola_annual_report_2023.pdf",
            )
            with fallback_path.open("rb") as fh:
                upload = client.post(
                    "/documents/upload",
                    headers=AUTH_HEADERS,
                    data={"company_id": str(company_id), "title": "Iberdrola Annual Report (fallback)"},
                    files={"file": (fallback_path.name, fh, "application/pdf")},
                )
            _write_json(
                logs_root / "fallback_upload.json",
                {"status_code": upload.status_code, "payload": _json_or_error(upload)},
            )
            inventory = client.get(f"/documents/inventory/{company_id}", headers=AUTH_HEADERS)
            inventory_payload = _json_or_error(inventory)
            _write_json(
                logs_root / "document_inventory_after_fallback.json",
                {"status_code": inventory.status_code, "payload": inventory_payload},
            )
            fallback_upload_used = True

        run_logs: list[dict[str, Any]] = []
        providers = ["deterministic_fallback", "local_lm_studio", "openai_cloud"]
        for provider in providers:
            baseline_log = _execute_run(
                client,
                company_id=company_id,
                provider=provider,
                research_provider="disabled",
                bundle_id=args.bundle_id,
                bundle_version=args.bundle_version,
                timeout_seconds=args.timeout_seconds,
            )
            run_logs.append(baseline_log)
            _write_json(
                logs_root / f"run_{baseline_log['run_id']}_{provider}_disabled.json",
                baseline_log,
            )

        # NotebookLM workflow checks:
        # 1) Internal research endpoint (actual NotebookLM integration path)
        # 2) Execute-run matrix with research_provider metadata set to notebooklm
        notebook_env = {
            "COMPLIANCE_APP_FEATURE_REG_RESEARCH_ENABLED": "true",
            "COMPLIANCE_APP_FEATURE_NOTEBOOKLM_ENABLED": "true",
            "COMPLIANCE_APP_FEATURE_NOTEBOOKLM_FAIL_OPEN": "false",
        }
        with _temporary_env(notebook_env):
            from apps.api.app.main import create_app as create_notebook_app

            notebook_app = create_notebook_app()
            notebook_client = TestClient(notebook_app, raise_server_exceptions=False)
            research = notebook_client.post(
                "/internal/regulatory-research/query",
                headers=AUTH_HEADERS,
                json={
                    "question": "Summarize ESRS E1 climate disclosure expectations for 2025 reporting.",
                    "corpus_key": "EU-CSRD-ESRS",
                    "mode": "qa",
                    "tags": ["iberdrola", "2025"],
                },
            )
            _write_json(
                logs_root / "notebook_internal_query.json",
                {"status_code": research.status_code, "payload": _json_or_error(research)},
            )

            for provider in providers:
                notebook_log = _execute_run(
                    notebook_client,
                    company_id=company_id,
                    provider=provider,
                    research_provider="notebooklm",
                    bundle_id=args.bundle_id,
                    bundle_version=args.bundle_version,
                    timeout_seconds=args.timeout_seconds,
                )
                run_logs.append(notebook_log)
                _write_json(
                    logs_root / f"run_{notebook_log['run_id']}_{provider}_notebooklm.json",
                    notebook_log,
                )

        summary = {
            "generated_at_utc": timestamp,
            "work_dir": str(root),
            "database_url": database_url,
            "company": company_payload,
            "bundle": {"id": args.bundle_id, "version": args.bundle_version},
            "fallback_upload_used": fallback_upload_used,
            "run_count": len(run_logs),
            "runs": [
                {
                    "run_id": int(row["run_id"]),
                    "provider": row["provider"],
                    "research_provider": row["research_provider"],
                    "terminal_status": row["terminal_status"],
                    "diagnostics_status_code": row["endpoints"]["diagnostics"]["status_code"],
                    "report_preview_status_code": row["endpoints"]["report_preview"]["status_code"],
                    "export_readiness_status_code": row["endpoints"]["export_readiness"]["status_code"],
                }
                for row in run_logs
            ],
        }
        _write_json(root / "summary.json", summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        print(f"\nDetailed logs written to: {logs_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
