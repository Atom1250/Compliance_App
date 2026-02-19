# Project State — Regulatory Registry + Obligations Conveyor

Next PR ID: PR-018

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
- PR-008 completed (A3 Part 1: safe evaluator context extension).
- Added `app/regulatory/safe_eval.py` with strict AST sandboxing for structured context expressions.
- Added explicit symbol whitelist enforcement and unknown symbol/attribute rejection behavior.
- Added tests in `tests/test_regulatory_safe_eval.py` for positive evaluation and rejection paths.
- Added PR execution log: `docs/prs/PR-008.md`.
- PR-009 completed (A3 Part 2: compiler core + compiled plan schema).
- Added `app/regulatory/compiler.py` with deterministic bundle compilation to applicable obligations/elements.
- Added compiled plan schema models and stable ordering for obligations/elements.
- Added phase-in rule handling through strict safe-eval evaluation.
- Added tests in `tests/test_regulatory_compiler.py` for deterministic ordering and phase-in behavior.
- Added PR execution log: `docs/prs/PR-009.md`.
- PR-010 completed (A3 Part 3: compile-from-DB adapter).
- Added `compile_from_db()` in `apps/api/app/services/regulatory_registry.py` to load stored payloads and compile plans.
- Added integration tests in `tests/test_regulatory_compile_from_db.py` covering sync->compile flow and missing-bundle failure.
- Preserved deterministic compile behavior by reusing schema validation + compiler ordering logic.
- Added PR execution log: `docs/prs/PR-010.md`.
- PR-011 completed (A4: CLI inspect/sync/preview interface).
- Added CLI helpers in `app/regulatory/cli.py` for listing bundles, filesystem sync, and compile preview from DB.
- Added `app/regulatory/__main__.py` entrypoint exposing `list`, `sync`, and `compile-preview` commands.
- Added tests in `tests/test_regulatory_cli.py` for sync/list/preview behavior and safe context JSON parsing.
- Added PR execution log: `docs/prs/PR-011.md`.
- PR-012 completed (B1: requirements extension + bundle-view adapter).
- Extended `app/requirements/schema.py` with optional obligations support while preserving legacy datapoint contracts.
- Added `app/requirements/bundle_view.py` with deterministic adapters for legacy datapoints and flattened obligation elements.
- Added back-compat tests in `tests/test_requirements_bundle_view.py` covering legacy bundle stability and obligations-native views.
- Added PR execution log: `docs/prs/PR-012.md`.
- PR-013 completed (B2 Part 1: company jurisdictions + compiler mode defaults).
- Added company fields `regulatory_jurisdictions` and `regulatory_regimes` with safe default `[]`.
- Added run field `compiler_mode` with default `legacy`.
- Added migration `0014_company_jurisdictions_and_run_compiler_mode.py`.
- Added persistence tests in `tests/test_regulatory_mode_defaults.py` validating defaults.
- Added PR execution log: `docs/prs/PR-013.md`.
- PR-014 completed (B2 Part 2: flagged registry datapoint generation).
- Added feature flag `feature_registry_compiler` (default OFF) in runtime config.
- Added deterministic generator `app/regulatory/datapoint_generation.py` for stable datapoint keys from compiled obligations.
- Added flagged registry branch in assessment pipeline P06 stage using `compile_from_db()` -> generated datapoints.
- Added tests in `tests/test_registry_mode_datapoints.py` for enabled registry mode and legacy-path behavior when flag is OFF.
- Added PR execution log: `docs/prs/PR-014.md`.
- PR-015 completed (B3 Part 1: manifest registry section + run-hash inputs).
- Extended run-hash inputs with `compiler_mode` and `registry_checksums` to avoid collisions across legacy/registry modes.
- Added registry manifest section (`retrieval_params.registry`) in registry mode, including bundle checksums.
- Updated execute-path tests for manifest payload and added registry-mode manifest coverage.
- Added PR execution log: `docs/prs/PR-015.md`.
- PR-016 completed (B3 Part 2: regulatory sync/compile audit events).
- Added `regulatory.sync.started|completed|failed` structured events in filesystem sync flow.
- Added `regulatory.compile.started|completed|failed` structured events in compile-from-DB flow.
- Added audit event tests in `tests/test_regulatory_audit_events.py`.
- Added PR execution log: `docs/prs/PR-016.md`.
- PR-017 completed (B4 Part 1: deterministic coverage matrix + flagged report section).
- Added deterministic registry coverage matrix computation in reporting service with stable obligation ordering.
- Added report matrix section gated by `feature_registry_report_matrix` (default OFF) and wired router rendering through runtime settings.
- Added tests in `tests/test_reporting.py` and `tests/test_registry_report_matrix_api.py` for deterministic computation and conditional rendering behavior.
- Added PR execution log: `docs/prs/PR-017.md`.

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
