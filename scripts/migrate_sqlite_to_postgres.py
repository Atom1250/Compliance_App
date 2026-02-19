#!/usr/bin/env python3
"""Migrate deterministic core records from SQLite to Postgres."""

from __future__ import annotations

import argparse
import json

from compliance_app.sqlite_to_postgres import migrate_sqlite_to_postgres


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate core compliance data from SQLite to Postgres")
    parser.add_argument("--sqlite-url", required=True, help="SQLite source URL")
    parser.add_argument("--postgres-url", required=True, help="Postgres destination URL")
    args = parser.parse_args()

    report = migrate_sqlite_to_postgres(sqlite_url=args.sqlite_url, postgres_url=args.postgres_url)
    print(
        json.dumps(
            {
                "source_url": report.source_url,
                "destination_url": report.destination_url,
                "tables": [
                    {
                        "table": table.table,
                        "source_count": table.source_count,
                        "destination_count": table.destination_count,
                        "source_hash": table.source_hash,
                        "destination_hash": table.destination_hash,
                        "inserted_rows": table.inserted_rows,
                        "updated_rows": table.updated_rows,
                    }
                    for table in report.tables
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
