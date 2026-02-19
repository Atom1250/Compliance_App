# PR-REGSRC-import-postgres

## Scope

- Added Postgres-backed `regulatory_source_document` schema via Alembic migration.
- Added ORM model for regulatory source documents.
- Added deterministic CSV/XLSX importer service with idempotent upsert behavior.
- Added CLI entrypoint for import + dry-run + issues CSV reporting.
- Added unit and integration tests (SQLite + optional Postgres harness).
- Added usage documentation for source register imports.

## Commands Used

- `python -m alembic upgrade head`
- `make lint`
- `make test`

## Notes

- XLSX import uses `openpyxl` if available in the runtime environment.
- URL validation records import issues; invalid URL rows are still imported for provenance review.
