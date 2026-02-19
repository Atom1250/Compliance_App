from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import (
    Company,
    DatapointAssessment,
    Document,
    Run,
    RunEvent,
    RunManifest,
)
from compliance_app.sqlite_to_postgres import migrate_sqlite_to_postgres


def _upgrade_to_head(url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")


def _seed_source_data(url: str) -> None:
    engine = create_engine(url)
    with Session(engine) as session:
        company = Company(
            name="Migration Co",
            tenant_id="default",
            reporting_year=2026,
            listed_status=True,
        )
        session.add(company)
        session.flush()

        document = Document(company_id=company.id, tenant_id="default", title="Source Report")
        session.add(document)
        session.flush()

        run = Run(
            company_id=company.id,
            tenant_id="default",
            status="completed",
            compiler_mode="legacy",
        )
        session.add(run)
        session.flush()

        session.add(
            DatapointAssessment(
                run_id=run.id,
                tenant_id="default",
                datapoint_key="ESRS-E1-1",
                status="Absent",
                value=None,
                evidence_chunk_ids=json.dumps([]),
                rationale="No evidence",
                model_name="deterministic_fallback",
                prompt_hash="prompt-hash",
                retrieval_params=json.dumps({"top_k": 5}),
            )
        )
        session.add(
            RunManifest(
                run_id=run.id,
                tenant_id="default",
                document_hashes=json.dumps(["abc123"]),
                bundle_id="esrs_mini",
                bundle_version="2026.01",
                retrieval_params=json.dumps({"top_k": 5}),
                model_name="deterministic_fallback",
                prompt_hash="prompt-hash",
                git_sha="deadbeef",
            )
        )
        session.add(
            RunEvent(
                run_id=run.id,
                tenant_id="default",
                event_type="run.execution.completed",
                payload=json.dumps({"status": "completed"}),
            )
        )
        session.commit()


def test_sqlite_to_postgres_migration_is_idempotent(tmp_path: Path) -> None:
    source_url = f"sqlite:///{tmp_path / 'source.sqlite'}"
    destination_url = f"sqlite:///{tmp_path / 'destination.sqlite'}"
    _upgrade_to_head(source_url)
    _upgrade_to_head(destination_url)
    _seed_source_data(source_url)

    first = migrate_sqlite_to_postgres(sqlite_url=source_url, postgres_url=destination_url)
    second = migrate_sqlite_to_postgres(sqlite_url=source_url, postgres_url=destination_url)

    first_by_table = {entry.table: entry for entry in first.tables}
    second_by_table = {entry.table: entry for entry in second.tables}

    assert first_by_table["company"].inserted_rows == 1
    assert first_by_table["document"].inserted_rows == 1
    assert first_by_table["run"].inserted_rows == 1
    assert first_by_table["run_manifest"].inserted_rows == 1
    assert first_by_table["run_event"].inserted_rows == 1
    assert first_by_table["datapoint_assessment"].inserted_rows == 1

    for table_name, first_report in first_by_table.items():
        second_report = second_by_table[table_name]
        assert second_report.inserted_rows == 0
        assert second_report.updated_rows == 0
        assert first_report.source_hash == second_report.source_hash
        assert second_report.source_hash == second_report.destination_hash
