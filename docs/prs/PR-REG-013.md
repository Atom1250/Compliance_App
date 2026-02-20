# PR-REG-013 — Obligation Coverage Matrix Persistence and Rendering

## Scope implemented
- Added `obligation_coverage` persistence table and service for deterministic obligation coverage aggregation.
- Persisted coverage rows keyed by compiled plan ID after assessment execution.
- Updated report rendering to include deterministic matrix sections (`Cross-cutting`, `E1`, `S1`, `G1`) even for sparse data.
- Updated golden snapshot contracts to include the matrix section deterministically.

## Commands run
- `make lint` ✅
- `make test` ✅
