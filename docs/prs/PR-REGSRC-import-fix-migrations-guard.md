# PR-REGSRC-import-fix-migrations-guard

## Scope

- Added importer guard for missing `regulatory_source_document` table with actionable migration error.
- Kept dry-run DB-independent so validation/issues reporting still works without schema.
- Relaxed optional date-field handling: unparseable optional dates are recorded in issues but do not invalidate rows.
- Updated CLI/help/docs to emphasize `SOURCE_SHEETS_*` CSV artifacts and discourage all-tabs CSV variants.
- Added tests for missing-table guard and SOURCE_SHEETS CSV validation behavior.

## Commands Run

- `.venv/bin/python -m alembic heads`
- `make lint`
- `make test`
