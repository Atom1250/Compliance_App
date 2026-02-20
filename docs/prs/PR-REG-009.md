# PR-REG-009 — Registry Compiler Activation and Relational Plan Persistence

## Scope implemented
- Added relational persistence models for compiled regulatory plans and obligations.
- Added migration to create `compiled_plan` and `compiled_obligation` and link `run_manifest.regulatory_plan_id`.
- Wired run execution to persist compiled plan rows and attach plan ID into run manifest.
- Added CSRD registry-mode guardrail: fail run when compiled obligations are empty.

## Commands run
- `make lint` ✅
- `make test` ✅

## Notes
- SQLite migration path uses Alembic batch alter for `run_manifest` FK compatibility in tests.
