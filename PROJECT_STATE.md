# Project State — Regulatory Registry + Obligations Conveyor

Next PR ID: PR-008

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
- PR-003 completed (A1 Part 2: loader + sample bundle).
- Added sample fixture bundle `app/regulatory/bundles/eu_csrd_sample.json` for registry/compiler test scaffolding.
- Added `app/regulatory/loader.py` to load + validate + return `(bundle, checksum, source_path)` deterministically.
- Added loader tests in `tests/test_regulatory_loader.py` covering deterministic checksum/path behavior and invalid payload rejection.
- Added PR execution log: `docs/prs/PR-003.md`.
- PR-004 completed (A2 Part 1: DB model + migration for regulatory bundles).
- Added ORM model `RegulatoryBundle` with `bundle_id`, `version`, `jurisdiction`, `regime`, `checksum`, and JSON `payload`.
- Added Alembic migration `0013_regulatory_bundle_table.py` to create/drop `regulatory_bundle` table and indexes.
- Extended migration tests to include regulatory table presence and explicit upgrade/downgrade smoke path.
- Added PR execution log: `docs/prs/PR-004.md`.
- PR-005 completed (A2 Part 2: registry store operations).
- Added `apps/api/app/services/regulatory_registry.py` with deterministic `upsert_bundle()` and `get_bundle()` operations.
- Implemented checksum-based idempotency/update behavior keyed by `bundle_id` + `version`.
- Added registry tests in `tests/test_regulatory_registry.py` for idempotent upsert, retrieval, and changed-payload checksum update.
- Added PR execution log: `docs/prs/PR-005.md`.
- PR-006 completed (A2 Part 3: filesystem sync).
- Added deterministic registry sync function `sync_from_filesystem()` to import all bundle JSON files from a root directory.
- Ensured deterministic processing order and idempotent behavior through sorted file traversal and upsert semantics.
- Added tests in `tests/test_regulatory_registry_sync.py` for repeatable sync outputs and stable ordering.
- Added PR execution log: `docs/prs/PR-006.md`.
- PR-007 completed (A2 Part 4: flagged startup sync hook).
- Added runtime config flags: `regulatory_registry_sync_enabled` and `regulatory_registry_bundles_root`.
- Added FastAPI startup hook that runs registry sync only when explicitly enabled.
- Added tests in `tests/test_regulatory_sync_startup.py` verifying the hook is off by default and executes when enabled.
- Added PR execution log: `docs/prs/PR-007.md`.

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
