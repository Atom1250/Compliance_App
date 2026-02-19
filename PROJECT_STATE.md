# Project State — Regulatory Registry + Obligations Conveyor

Next PR ID: PR-003

## Completed Work
- PR-001 completed (Phase 0 bootstrap + baseline lock).
- Verified mandatory conveyor artifacts exist: `PROJECT_STATE.md`, `docs/PR_CONVEYOR_PLAN.md`, `.github/pull_request_template.md`, `.github/codex/prompts/meta_next_pr.md`.
- Verified ADR-0001 path exists and is readable at `docs/adr/0001-architecture.md`.
- Added legacy regression guardrail test: `tests/test_legacy_requirements_resolution_stability.py`.
- Added PR execution log: `docs/prs/PR-001.md`.
- PR-002 completed (A1 Part 1: schema + canonicalization).
- Added `app/regulatory/schema.py` with minimal validated bundle models (`RegulatoryBundle`, `Obligation`, `Element`, `PhaseInRule`).
- Added `app/regulatory/canonical.py` with deterministic canonical JSON and SHA-256 checksum helpers.
- Added unit tests in `tests/test_regulatory_schema_and_canonical.py` for schema acceptance/rejection and checksum stability/change sensitivity.
- Added PR execution log: `docs/prs/PR-002.md`.

## Tooling Notes
- Test command: `make test` (`.venv/bin/python -m pytest`)
- Lint command: `make lint` (`.venv/bin/python -m ruff check src apps tests`)
- Format command: no dedicated formatter target (ruff-only lint gate currently)
- Typecheck command: none configured
- Migration tooling: Alembic (`alembic.ini`, `alembic/versions/`, `alembic upgrade head`)
- Baseline PR-001 test run: `make test` -> `107 passed, 1 warning`

## Open Risks / Unknowns
- [ ] Confirm migrations framework and how to run upgrade/downgrade in CI.
- [ ] Confirm existing auth pattern for admin endpoints (or decide CLI-only for PR-011).
- [ ] Confirm where feature flags/config lives and naming conventions.
- [ ] Confirm test DB strategy (sqlite? postgres? docker service?).
- [ ] `pytest` warns on unknown config key `asyncio_default_fixture_loop_scope`; cleanup needed to avoid config drift.

## Repository Conventions
- Branch naming: `pr-XXX-<short-name>`
- Commit message: `PR-XXX: <short summary>`
- Required checks: `make lint`, `make test`

## Notes
- This file is updated every PR:
  - Add PR to Completed Work (2–5 bullets)
  - Advance Next PR ID to the next PR in docs/PR_CONVEYOR_PLAN.md
  - Record any new blockers/risks
