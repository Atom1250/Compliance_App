# PR-REG-011 — Retrieval/Verification Contract Hardening

## Scope implemented
- Added extraction diagnostics persistence (`extraction_diagnostics`) for per-datapoint retrieval/verification trace.
- Added explicit failure reason codes (`CHUNK_NOT_FOUND`, `EMPTY_CHUNK`, `NUMERIC_MISMATCH`, `BASELINE_MISSING`).
- Hardened verification so orphan/missing cited chunks and empty cited text downgrade to `Absent` deterministically.
- Added regression tests for verification downgrade behavior and diagnostics persistence.

## Commands run
- `make lint` ✅
- `make test` ✅
