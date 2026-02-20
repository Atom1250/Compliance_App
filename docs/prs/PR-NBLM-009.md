# PR-NBLM-009 — CI Stub Provider Safety Harness

## Checklist
- Added deterministic `StubResearchProvider`.
- Added provider factory to select stub when NotebookLM is disabled.
- Added tests for stub-path factory behavior and internal route gating behavior.
- Added manual NotebookLM integration test runbook (non-CI).

## Commands
- `make lint` ✅
- `make test` ✅
