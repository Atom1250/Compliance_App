# PR-REGSRC-import-fix-document-name

## Scope

- Made `document_name` optional during regulatory source CSV import.
- Kept `record_id` and `jurisdiction` as the only hard-required fields.
- Added deterministic fallback `document_name` derived from `record_id` (and optional `legal_reference` suffix).
- Added SOURCE_SHEETS fixture test with 30 rows confirming `invalid_rows=0` and idempotent re-import behavior.
- Updated import docs to reflect required vs recommended fields.

## Validation

- `make lint`
- `make test`
