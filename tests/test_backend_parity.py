from __future__ import annotations

import os
import uuid
from contextlib import suppress
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError

from compliance_app.backend_parity import compare_backend_parity
from compliance_app.postgres_e2e import run_postgres_e2e
from compliance_app.uat_harness import run_uat_harness


def test_backend_parity_normalization_ignores_nondeterministic_fields() -> None:
    sqlite_summary = {
        "flow": {"terminal_status": "completed"},
        "manifest": {
            "bundle_id": "esrs_mini",
            "bundle_version": "2026.01",
            "retrieval_policy_version": "hybrid-v1",
            "retrieval_top_k": 5,
        },
        "evidence_pack": {"manifest_file_count": 3},
        "scenario_results": [
            {
                "id": "local_deterministic_success",
                "report_ready": True,
                "evidence_pack_ready": True,
                "report_status_code": 200,
                "evidence_preview_status_code": 200,
                "blocking_reasons": [],
            }
        ],
        "run_id": 999,
    }
    postgres_summary = {
        "run_id": 1,
        "terminal_status": "completed",
        "bundle_id": "esrs_mini",
        "bundle_version": "2026.01",
        "retrieval_policy_version": "hybrid-v1",
        "retrieval_top_k": 5,
        "report_ready": True,
        "evidence_pack_ready": True,
        "blocking_reasons": [],
        "report_status_code": 200,
        "evidence_preview_status_code": 200,
        "evidence_file_count": 3,
    }

    comparison = compare_backend_parity(
        sqlite_summary=sqlite_summary,
        postgres_summary=postgres_summary,
    )
    assert comparison.is_equal is True
    assert comparison.mismatches == []


@pytest.mark.skipif(
    not os.getenv("COMPLIANCE_APP_POSTGRES_TEST_URL"),
    reason="COMPLIANCE_APP_POSTGRES_TEST_URL is not configured",
)
def test_backend_parity_between_sqlite_and_postgres_harnesses(tmp_path: Path) -> None:
    base_url = make_url(os.environ["COMPLIANCE_APP_POSTGRES_TEST_URL"])
    db_name = f"compliance_parity_{uuid.uuid4().hex[:10]}"
    admin_url = base_url.set(database="postgres")
    target_url = base_url.set(database=db_name)

    admin_engine = create_engine(str(admin_url), isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    except OperationalError as exc:
        pytest.skip(f"postgres test user lacks database create privileges: {exc}")

    try:
        sqlite_summary = run_uat_harness(work_dir=tmp_path / "sqlite-uat")
        postgres_summary = run_postgres_e2e(
            database_url=str(target_url),
            work_dir=tmp_path / "postgres-uat",
        )
        comparison = compare_backend_parity(
            sqlite_summary=sqlite_summary,
            postgres_summary=postgres_summary,
        )
        assert comparison.is_equal is True
        assert comparison.mismatches == []
    finally:
        with admin_engine.connect() as conn:
            with suppress(Exception):
                conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        admin_engine.dispose()
