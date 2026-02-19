import os
import uuid
from contextlib import suppress
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError

from compliance_app.postgres_e2e import run_postgres_e2e


@pytest.mark.skipif(
    not os.getenv("COMPLIANCE_APP_POSTGRES_TEST_URL"),
    reason="COMPLIANCE_APP_POSTGRES_TEST_URL is not configured",
)
def test_postgres_e2e_harness_executes_full_flow(tmp_path: Path) -> None:
    base_url = make_url(os.environ["COMPLIANCE_APP_POSTGRES_TEST_URL"])
    db_name = f"compliance_e2e_{uuid.uuid4().hex[:10]}"
    admin_url = base_url.set(database="postgres")
    target_url = base_url.set(database=db_name)

    admin_engine = create_engine(str(admin_url), isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    except OperationalError as exc:
        pytest.skip(f"postgres test user lacks database create privileges: {exc}")

    try:
        summary = run_postgres_e2e(database_url=str(target_url), work_dir=tmp_path / "postgres-e2e")
        assert summary["terminal_status"] == "completed"
        assert summary["bundle_id"] == "esrs_mini"
        assert summary["bundle_version"] == "2026.01"
        assert summary["report_ready"] is True
        assert summary["evidence_pack_ready"] is True
        assert summary["blocking_reasons"] == []
        assert summary["report_status_code"] == 200
        assert summary["evidence_preview_status_code"] == 200
        assert int(summary["evidence_file_count"]) > 0
    finally:
        with admin_engine.connect() as conn:
            with suppress(Exception):
                conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        admin_engine.dispose()
