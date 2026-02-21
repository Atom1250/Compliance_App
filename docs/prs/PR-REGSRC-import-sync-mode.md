# PR-REGSRC-import-sync-mode

## Scope

- Added explicit importer mode support: `merge` (default) and `sync`.
- Added CLI `--mode {merge,sync}` and updated examples.
- Implemented sync semantics (`clear-on-empty`) for mutable fields while preserving immutable fields.
- Added tests covering merge retention, sync clearing, and sync idempotency.
- Updated importer docs with a "Merge vs Sync modes" section.

## Validation

- `make lint`
- `make test`
