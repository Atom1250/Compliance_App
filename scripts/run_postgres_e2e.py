#!/usr/bin/env python3
"""Run the Postgres end-to-end harness and print a compact summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
from compliance_app.postgres_e2e import run_postgres_e2e


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Postgres E2E compliance flow")
    parser.add_argument("--database-url", required=True, help="Postgres database URL")
    parser.add_argument(
        "--work-dir",
        default="outputs/postgres-e2e",
        help="Working directory for object store and evidence outputs",
    )
    args = parser.parse_args()

    summary = run_postgres_e2e(database_url=args.database_url, work_dir=Path(args.work_dir))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
