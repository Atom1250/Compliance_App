# PR Conveyor Plan — Regulatory Registry + Obligations-Driven Runs

This roadmap implements two overhauls:
1) Regulatory & Jurisdictional Registry (DB-backed, versioned, compiler)
2) Obligations-driven requirements resolution + coverage matrix reporting

General rules:
- Each PR is atomic (~30–90 minutes).
- Implement ONLY the scope of the current PR.
- Always add/adjust tests listed.
- Always run: `make lint` and `make test`.
- Preserve determinism, evidence gating, schema-first outputs, and reproducible manifests.

For every PR:
- Create/update `docs/prs/PR-XXX.md` with checklist + commands run + results.
- Update `PROJECT_STATE.md` Completed Work + advance Next PR ID.

---

## PR-001 — Phase 0: Bootstrap Conveyor + Baseline Lock

Objective:
Bootstrap the PR conveyor workflow and lock baseline legacy behavior with a regression test.

Scope:
- Ensure: PROJECT_STATE.md, docs/PR_CONVEYOR_PLAN.md, .github/pull_request_template.md exist
- Ensure: .github/codex/prompts/meta_next_pr.md exists and matches the meta prompt semantics
- Ensure `docs/adr/0001-architecture.md` exists and contains ADR-0001 content
- Ensure `make lint` and `make test` exist
- Add a regression test for legacy requirements resolution path stability
- Add docs/prs/PR-001.md execution log

Definition of Done:
- `make lint` and `make test` pass
- Regression test added and passes
- PROJECT_STATE updated, Next PR ID = PR-002

Tests:
- `make lint`
- `make test`

---

## PR-002 — A1 (Part 1): Regulatory Schema + Canonicalization

Objective:
Add validated regulatory bundle schema + deterministic canonical JSON hashing.

Scope:
- Add `app/regulatory/schema.py` (Pydantic models: RegulatoryBundle, Obligation, Element, PhaseInRule minimal v1)
- Add `app/regulatory/canonical.py` for canonicalization + sha256 checksum
- Add unit tests for schema validation + checksum stability

Definition of Done:
- Schema validates and rejects invalid payloads
- Checksum stable across repeated loads
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-003 — A1 (Part 2): Bundle Loader + Sample Bundle
Objective:
Add filesystem loader and a tiny sample bundle for compile fixtures.

Scope:
- Add minimal EU sample bundle JSON under `app/regulatory/bundles/...`
- Add `app/regulatory/loader.py` to load + validate + return `(bundle, checksum, source_path)`
- Add loader tests

Definition of Done:
- Loader deterministic and rejects invalid bundles
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-004 — A2 (Part 1): DB Model + Migration for regulatory_bundle
Objective:
Create DB storage for regulatory bundles (JSONB payload + checksum + versioning).

Scope:
- ORM model for `regulatory_bundle` (repo conventions)
- Migration create table + downgrade
- Migration tests/smoke

Definition of Done:
- Migration upgrade/downgrade succeeds
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-005 — A2 (Part 2): Registry Store (upsert/get) + Checksums
Objective:
Implement DB store operations for bundles with checksum verification.

Scope:
- `apps/api/app/services/regulatory_registry.py`: upsert/get
- Tests for idempotency and retrieval

Definition of Done:
- Upsert idempotent; checksum stored/returned
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-006 — A2 (Part 3): Sync From Filesystem (Idempotent)
Objective:
Deterministic sync from repo bundles → DB.

Scope:
- `sync_from_filesystem()` implementation + tests

Definition of Done:
- Sync idempotent, deterministic
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-007 — A2 (Part 4): Startup/CLI Sync Hook (Flagged)
Objective:
Run sync via startup hook or CLI/management command, behind a feature flag.

Scope:
- Add flagged hook/command
- Tests verify it’s gated by flag

Definition of Done:
- Hook exists and is gated; defaults safe
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-008 — A3 (Part 1): Safe Evaluator Context Extension
Objective:
Extend safe evaluator to support structured context with strict whitelisting.

Scope:
- Update safe evaluator module
- Add tests for whitelist and unknown symbol rejection

Definition of Done:
- Evaluator remains sandboxed
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-009 — A3 (Part 2): Compiler Core + Compiled Plan Schema
Objective:
Compile bundles → applicable obligations/elements with stable ordering; serialize compiled plan.

Scope:
- `app/regulatory/compiler.py` + `CompiledRegulatoryPlan` schema
- Tests for deterministic ordering + phase-in behavior

Definition of Done:
- Compiler output stable; tests pass

Tests:
- `make lint`
- `make test`

---

## PR-010 — A3 (Part 3): compile_from_db Adapter
Objective:
Load bundles from DB and compile into a plan.

Scope:
- `compile_from_db()` in registry service
- DB integration test: sync → compile

Definition of Done:
- Adapter works end-to-end; tests pass

Tests:
- `make lint`
- `make test`

---

## PR-011 — A4: Admin/Debug Interfaces OR CLI Preview
Objective:
Safe inspectability (admin endpoints if auth exists, otherwise CLI).

Scope:
- Admin endpoints OR CLI for list/sync/compile-preview (gated + safe)

Definition of Done:
- At least one safe interface exists; tests pass

Tests:
- `make lint`
- `make test`

---

## PR-012 — B1: Requirements Bundle Extension + Bundle View Adapter
Objective:
Support obligations-native bundles while keeping legacy bundles working unchanged.

Scope:
- Optional obligations in schema OR adapter
- `bundle_view.py` iterator API
- Back-compat tests

Definition of Done:
- Legacy unchanged; obligations accessible; tests pass

Tests:
- `make lint`
- `make test`

---

## PR-013 — B2 (Part 1): Company Jurisdictions + Run Config Mode (Defaults legacy)
Objective:
Add fields needed to select registry compiler mode safely.

Scope:
- Company jurisdictions/regimes default safe
- Run compiler mode field default legacy
- Tests for defaults and persistence

Definition of Done:
- Fields exist; legacy unaffected; tests pass

Tests:
- `make lint`
- `make test`

---

## PR-014 — B2 (Part 2): P06 Registry Mode Generates Datapoints (Flagged)
Objective:
P06 branch uses compiled obligations to generate datapoints without changing P07–P10.

Scope:
- Feature flag `FEATURE_REGISTRY_COMPILER` default OFF
- Registry mode: compile_from_db → generate datapoints with stable keys
- Tests for deterministic generation

Definition of Done:
- Registry mode works behind flag; legacy unchanged; tests pass

Tests:
- `make lint`
- `make test`

---

## PR-015 — B3 (Part 1): Manifest Registry Section + Run Hash Inputs
Objective:
Prevent cache collisions and ensure reproducibility in registry mode.

Scope:
- Manifest includes registry section (registry mode only)
- Run hash includes compiler mode + checksums
- Tests for hash/manifest

Definition of Done:
- No collisions; tests pass

Tests:
- `make lint`
- `make test`

---

## PR-016 — B3 (Part 2): Audit Events for Sync + Compile
Objective:
Emit audit events for sync/compile.

Scope:
- Add `regulatory.sync.*` + `regulatory.compile.*` events
- Tests for emission

Definition of Done:
- Events emitted; tests pass

Tests:
- `make lint`
- `make test`

---

## PR-017 — B4 (Part 1): Coverage Matrix Computation + Report Rendering (Flagged)
Objective:
Compute obligation-level compliance deterministically and render report matrix behind flag.

Scope:
- Coverage computation
- Report matrix section behind `FEATURE_REGISTRY_REPORT_MATRIX` default OFF
- Tests

Definition of Done:
- Coverage deterministic; report conditional; tests pass

Tests:
- `make lint`
- `make test`

---

## PR-018 — B4 (Part 2): Evidence Pack Includes Registry Artifacts
Objective:
Add compiled plan + coverage outputs to evidence pack ZIP.

Scope:
- Evidence pack includes registry artifacts in registry mode
- Tests for ZIP contents

Definition of Done:
- Artifacts included; tests pass

Tests:
- `make lint`
- `make test`

---

## PR-019 — B5: Seed Minimal Bundles + Sync→Compile End-to-End Tests
Objective:
Ship minimal EU/UK/NO + green finance bundles and end-to-end sync/compile tests.

Scope:
- Seed bundles
- End-to-end test: FS → DB sync → compile plan determinism

Definition of Done:
- Bundles validate/sync/compile; tests pass

Tests:
- `make lint`
- `make test`

---

## PR-020 — B6: Persist Run-Scoped Registry Artifacts (Determinism Lock)
Objective:
Store compiled registry plan + coverage matrix as run-scoped artifacts during execution, then serve evidence/report exports from persisted artifacts (not live recompilation).

Scope:
- Add run-scoped storage for registry artifacts (compiled plan JSON + coverage matrix JSON)
- Persist artifacts during run execution when `compiler_mode=registry`
- Update evidence pack export to read persisted artifacts (fallback: omit artifacts if missing)
- Keep behavior unchanged for legacy mode
- Add deterministic tests for:
  - persisted artifact content stability across repeated exports
  - export behavior does not depend on current registry DB state after run completion

Definition of Done:
- Registry run outputs are reproducible from run-scoped persisted artifacts
- Evidence pack no longer recompiles registry plan at export time
- Tests pass

Tests:
- `make lint`
- `make test`
