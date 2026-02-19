from __future__ import annotations

import csv
import os
import uuid
from contextlib import suppress
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import RegulatorySourceDocument
from apps.api.app.services.regulatory_sources_import import (
    ImportIssue,
    _merge_rows,
    _normalize_row,
    canonical_row_checksum,
    import_regulatory_sources,
)


def _prepare_sqlite_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "regsrc_import.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    return Session(engine, expire_on_commit=False)


def _fixture_path() -> Path:
    return Path("tests/fixtures/regulatory_sources_eu_sample.csv")


def test_normalization_tags_dates_and_url_validation() -> None:
    issues: list[ImportIssue] = []
    normalized = _normalize_row(
        row={
            "record_id": " EU-X ",
            "jurisdiction": " EU ",
            "document_name": " Sample ",
            "keywords_tags": " climate | climate ; risks ",
            "effective_date": "2024",
            "last_checked_date": "2024-99-99",
            "official_source_url": "ftp://invalid.example",
        },
        row_number=2,
        sheet="csv",
        issues=issues,
    )
    assert normalized is not None
    assert normalized["keywords_tags"] == "climate|risks"
    assert normalized["effective_date"].isoformat() == "2024-01-01"
    assert normalized["last_checked_date"] is None
    assert normalized["official_source_url"] == "ftp://invalid.example"
    assert len(issues) == 2
    issue_fields = {issue.field for issue in issues}
    assert issue_fields == {"official_source_url", "last_checked_date"}


def test_source_sheets_csv_import_has_zero_invalid_rows(tmp_path: Path) -> None:
    source_sheets_csv = tmp_path / "regulatory_source_document_SOURCE_SHEETS_full.csv"
    source_sheets_csv.write_text(
        "record_id,jurisdiction,document_name,effective_date,last_checked_date,official_source_url\n"
        "EU-L1-CSRD,EU,CSRD,2022,2025/01/15,https://eur-lex.europa.eu\n"
        "EU-L2-ESRS-DA,EU,ESRS DA,2023-07-31,2025-99-99,https://eur-lex.europa.eu\n",
        encoding="utf-8",
    )
    with _prepare_sqlite_session(tmp_path) as session:
        summary = import_regulatory_sources(
            session,
            file_path=source_sheets_csv,
            dry_run=True,
            issues_out=tmp_path / "issues.csv",
        )
    assert summary.rows_seen == 2
    assert summary.rows_deduped == 2
    assert summary.invalid_rows == 0


def test_missing_table_guard_returns_clear_error(tmp_path: Path) -> None:
    source_csv = tmp_path / "regulatory_source_document_SOURCE_SHEETS_full.csv"
    source_csv.write_text(
        "record_id,jurisdiction,document_name\nEU-L1-CSRD,EU,CSRD\n",
        encoding="utf-8",
    )
    engine = create_engine("sqlite:///:memory:")
    with Session(engine, expire_on_commit=False) as session:
        with pytest.raises(ValueError) as exc:
            import_regulatory_sources(session, file_path=source_csv, dry_run=False)
    assert (
        "Table regulatory_source_document does not exist. "
        "Apply migrations (alembic upgrade head) then retry."
        in str(exc.value)
    )


def test_checksum_is_deterministic_for_canonical_row() -> None:
    row_one = {
        "record_id": "EU-X",
        "jurisdiction": "EU",
        "document_name": "Document",
        "keywords_tags": "climate|risk",
        "source_sheets": "Sheet1",
        "effective_date": None,
        "last_checked_date": None,
    }
    row_two = {
        "document_name": "Document",
        "jurisdiction": "EU",
        "record_id": "EU-X",
        "keywords_tags": "climate|risk",
        "source_sheets": "Sheet1",
        "effective_date": None,
        "last_checked_date": None,
    }
    assert canonical_row_checksum(row_one) == canonical_row_checksum(row_two)


def test_dedup_merge_uses_first_non_empty_values() -> None:
    base = {
        "record_id": "EU-X",
        "jurisdiction": "EU",
        "document_name": "Doc",
        "document_type": None,
        "source_sheets": "Master_Documents",
    }
    incoming = {
        "record_id": "EU-X",
        "jurisdiction": "EU",
        "document_name": "Doc",
        "document_type": "Directive",
        "source_sheets": "ESRS_Standards",
    }
    merged = _merge_rows(base, incoming, sheet="ESRS_Standards")
    assert merged["document_type"] == "Directive"
    assert merged["source_sheets"] == "ESRS_Standards|Master_Documents"


def test_importer_is_idempotent_for_same_file(tmp_path: Path) -> None:
    issues_file = tmp_path / "issues.csv"
    with _prepare_sqlite_session(tmp_path) as session:
        first = import_regulatory_sources(
            session,
            file_path=_fixture_path(),
            jurisdiction="EU",
            dry_run=False,
            issues_out=issues_file,
        )
        second = import_regulatory_sources(
            session,
            file_path=_fixture_path(),
            jurisdiction="EU",
            dry_run=False,
            issues_out=issues_file,
        )
        records = session.scalars(
            select(RegulatorySourceDocument).order_by(RegulatorySourceDocument.record_id)
        ).all()

    assert first.inserted == 4
    assert first.updated == 0
    assert second.inserted == 0
    assert second.updated == 0
    assert second.skipped == 4
    assert len(records) == 4
    assert issues_file.exists()
    with issues_file.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["field"] == "official_source_url"


@pytest.mark.skipif(
    not os.getenv("COMPLIANCE_APP_POSTGRES_TEST_URL"),
    reason="COMPLIANCE_APP_POSTGRES_TEST_URL is not configured",
)
def test_importer_postgres_round_trip_smoke(tmp_path: Path) -> None:
    base_url = make_url(os.environ["COMPLIANCE_APP_POSTGRES_TEST_URL"])
    db_name = f"regsrc_import_{uuid.uuid4().hex[:10]}"
    admin_url = base_url.set(database="postgres")
    target_url = base_url.set(database=db_name)

    admin_engine = create_engine(str(admin_url), isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    except OperationalError as exc:
        pytest.skip(f"postgres test user lacks database create privileges: {exc}")

    engine = None
    try:
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", str(target_url))
        command.upgrade(config, "head")
        engine = create_engine(str(target_url))
        with Session(engine, expire_on_commit=False) as session:
            first = import_regulatory_sources(
                session,
                file_path=_fixture_path(),
                jurisdiction="EU",
                dry_run=False,
            )
            second = import_regulatory_sources(
                session,
                file_path=_fixture_path(),
                jurisdiction="EU",
                dry_run=False,
            )
            count = int(
                session.scalar(select(func.count()).select_from(RegulatorySourceDocument)) or 0
            )
        assert first.inserted == 4
        assert second.skipped == 4
        assert count == 4
    finally:
        if engine is not None:
            with suppress(Exception):
                engine.dispose()
        with admin_engine.connect() as conn:
            with suppress(Exception):
                conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        admin_engine.dispose()
