"""Deterministic SQLite -> Postgres migration utility for core workflow tables."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import MetaData, and_, create_engine, inspect, select, table
from sqlalchemy.engine import Engine

DEFAULT_TABLES: tuple[str, ...] = (
    "company",
    "document",
    "document_file",
    "document_page",
    "chunk",
    "embedding",
    "run",
    "run_event",
    "run_materiality",
    "datapoint_assessment",
    "run_manifest",
    "run_cache_entry",
    "run_registry_artifact",
    "run_input_snapshot",
)


@dataclass(frozen=True)
class TableMigrationReport:
    table: str
    source_count: int
    destination_count: int
    source_hash: str
    destination_hash: str
    inserted_rows: int
    updated_rows: int


@dataclass(frozen=True)
class MigrationReport:
    source_url: str
    destination_url: str
    tables: list[TableMigrationReport]


def _normalize_scalar(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat(timespec="microseconds")
    if isinstance(value, Decimal):
        return str(value)
    return value


def _normalized_row(row: dict[str, object]) -> dict[str, object]:
    return {column: _normalize_scalar(value) for column, value in row.items()}


def _row_hash(rows: list[dict[str, object]]) -> str:
    payload = json.dumps(
        [_normalized_row(row) for row in rows],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_rows(engine: Engine, table_name: str) -> tuple[list[dict[str, object]], list[str]]:
    metadata = MetaData()
    db_table = table(table_name)
    metadata.reflect(bind=engine, only=[table_name])
    db_table = metadata.tables[table_name]

    inspector = inspect(engine)
    pk_columns = inspector.get_pk_constraint(table_name).get("constrained_columns") or ["id"]
    order_by_columns = [db_table.c[column] for column in pk_columns if column in db_table.c]

    with engine.connect() as conn:
        rows = conn.execute(select(db_table).order_by(*order_by_columns)).mappings().all()

    return [dict(row) for row in rows], pk_columns


def migrate_sqlite_to_postgres(
    *,
    sqlite_url: str,
    postgres_url: str,
    tables: tuple[str, ...] = DEFAULT_TABLES,
) -> MigrationReport:
    source_engine = create_engine(sqlite_url)
    destination_engine = create_engine(postgres_url)

    source_inspector = inspect(source_engine)
    destination_inspector = inspect(destination_engine)

    reports: list[TableMigrationReport] = []

    for table_name in tables:
        if table_name not in source_inspector.get_table_names():
            continue
        if table_name not in destination_inspector.get_table_names():
            continue

        source_rows, pk_columns = _load_rows(source_engine, table_name)
        metadata = MetaData()
        metadata.reflect(bind=destination_engine, only=[table_name])
        dest_table = metadata.tables[table_name]
        destination_columns = {column.name for column in dest_table.columns}

        inserted_rows = 0
        updated_rows = 0

        with destination_engine.begin() as conn:
            for source_row in source_rows:
                payload = {
                    key: value for key, value in source_row.items() if key in destination_columns
                }
                where_clause = and_(*[dest_table.c[col] == payload[col] for col in pk_columns])
                existing = conn.execute(select(dest_table).where(where_clause)).mappings().first()
                if existing is None:
                    conn.execute(dest_table.insert().values(**payload))
                    inserted_rows += 1
                    continue

                existing_payload = _normalized_row({key: existing[key] for key in payload})
                source_payload = _normalized_row(payload)
                if existing_payload != source_payload:
                    conn.execute(dest_table.update().where(where_clause).values(**payload))
                    updated_rows += 1

        destination_rows, _ = _load_rows(destination_engine, table_name)
        reports.append(
            TableMigrationReport(
                table=table_name,
                source_count=len(source_rows),
                destination_count=len(destination_rows),
                source_hash=_row_hash(source_rows),
                destination_hash=_row_hash(destination_rows),
                inserted_rows=inserted_rows,
                updated_rows=updated_rows,
            )
        )

    return MigrationReport(
        source_url=sqlite_url,
        destination_url=postgres_url,
        tables=reports,
    )
