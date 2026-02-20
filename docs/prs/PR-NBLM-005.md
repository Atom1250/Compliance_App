# PR-NBLM-005 — Requirement-Linked Research Notes Persistence

## Checklist
- Added migration/model for `regulatory_requirement_research_notes`.
- Added notes repository (`insert`, `list`).
- Extended service with citation-gated `query_and_maybe_persist`.
- Added tests for persistence enabled/disabled and citation constraints.

## Commands
- `make lint` ✅
- `make test` ✅
