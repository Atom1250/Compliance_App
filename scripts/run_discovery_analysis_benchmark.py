#!/usr/bin/env python3
"""Run deterministic A/B benchmark for discovery + analysis quality."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))


def _wait_for_status(
    client: TestClient,
    *,
    run_id: int,
    headers: dict[str, str],
    timeout_seconds: float = 90.0,
) -> str:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        response = client.get(f"/runs/{run_id}/status", headers=headers)
        response.raise_for_status()
        status = str(response.json().get("status", "unknown"))
        if status in {"completed", "failed"}:
            return status
        time.sleep(1.0)
    return "timeout"


def main() -> int:
    from apps.api.app.main import create_app

    parser = argparse.ArgumentParser(description="Run discovery+analysis benchmark")
    parser.add_argument("--company-name", required=True)
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
    parser.add_argument("--bundle-id", default="esrs_mini")
    parser.add_argument("--bundle-version", default="2024.01")
    parser.add_argument("--max-documents", type=int, default=8)
    parser.add_argument(
        "--providers",
        default="local_lm_studio,openai_cloud",
        help="Comma-delimited providers",
    )
    parser.add_argument("--out", default="outputs/benchmark/discovery_analysis_ab.json")
    args = parser.parse_args()

    app = create_app()
    client = TestClient(app)
    headers = {
        "X-API-Key": os.getenv("COMPLIANCE_APP_API_KEY", "dev-key"),
        "X-Tenant-ID": os.getenv("COMPLIANCE_APP_TENANT_ID", "default"),
    }

    company = client.post(
        "/companies",
        headers=headers,
        json={
            "name": args.company_name,
            "listed_status": True,
            "reporting_year_start": args.year_start,
            "reporting_year_end": args.year_end,
        },
    )
    company.raise_for_status()
    company_id = int(company.json()["id"])

    discovery = client.post(
        "/documents/auto-discover",
        headers=headers,
        json={"company_id": company_id, "max_documents": args.max_documents},
    )
    discovery.raise_for_status()
    discovery_payload = discovery.json()

    provider_rows: list[dict[str, object]] = []
    for provider in [item.strip() for item in args.providers.split(",") if item.strip()]:
        run = client.post("/runs", headers=headers, json={"company_id": company_id})
        run.raise_for_status()
        run_id = int(run.json()["run_id"])

        execute = client.post(
            f"/runs/{run_id}/execute",
            headers=headers,
            json={
                "bundle_id": args.bundle_id,
                "bundle_version": args.bundle_version,
                "llm_provider": provider,
            },
        )
        execute.raise_for_status()
        final_status = _wait_for_status(client, run_id=run_id, headers=headers)

        diagnostics = client.get(f"/runs/{run_id}/diagnostics", headers=headers)
        diagnostics_payload = diagnostics.json() if diagnostics.status_code == 200 else {}
        preview = client.get(f"/runs/{run_id}/report-preview", headers=headers)
        preview_payload = preview.json() if preview.status_code == 200 else {}
        provider_rows.append(
            {
                "provider": provider,
                "run_id": run_id,
                "final_status": final_status,
                "diagnostics": diagnostics_payload,
                "report_preview_status_code": preview.status_code,
                "report_summary": preview_payload.get("summary"),
                "report_metrics": preview_payload.get("metrics"),
            }
        )

    summary = {
        "company": {
            "id": company_id,
            "name": args.company_name,
            "year_start": args.year_start,
            "year_end": args.year_end,
        },
        "discovery": discovery_payload,
        "providers": provider_rows,
    }

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
