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

---

## PR-021 — C1: Deterministic Run Diagnostics API
Objective:
Add a deterministic diagnostics endpoint to expose run pipeline stage outcomes and failure context.

Scope:
- Add `GET /runs/{run_id}/diagnostics` (tenant scoped)
- Include deterministic fields:
  - run status
  - manifest presence
  - required datapoints count (when derivable)
  - assessment count and status histogram
  - retrieval hit count (unique cited chunks)
  - latest failure reason from run events
- Add API contract tests including failure-run coverage

Definition of Done:
- Endpoint returns stable diagnostics payload for identical DB state
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-022 — C2: Discovery Hardening (PDF-only + Deterministic Ranking)
Objective:
Ensure document auto-discovery is strict, auditable, and deterministic.

Scope:
- Enforce PDF-only candidate acceptance
- Add deterministic ranking and explicit tie-break
- Persist accepted/rejected candidate reasons
- Add tests for file-type filtering and ranking determinism

Definition of Done:
- Non-PDF pages rejected by design
- Ranking stable across repeated runs
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-023 — C3: Ingestion Contract Stabilization
Objective:
Stabilize manual and auto-ingestion contracts to prevent upload path regressions.

Scope:
- Normalize required upload metadata validation across endpoints
- Improve 4xx error detail consistency for missing/invalid fields
- Add integration tests for 422 and successful upload paths

Definition of Done:
- Upload APIs fail clearly and consistently for invalid payloads
- Existing happy-path behavior preserved
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-024 — C4: Parser + Chunk Determinism Golden Tests
Objective:
Lock deterministic parsing/chunking behavior with repeatable goldens.

Scope:
- Add golden test fixtures for chunk ID stability
- Validate deterministic offsets/order for repeated ingestion
- Add parser-version pin checks in tests

Definition of Done:
- Determinism regressions in chunk IDs/ordering are caught by tests
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-025 — C5: Retrieval Explainability Artifacts
Objective:
Persist deterministic retrieval traces for auditability.

Scope:
- Store per-datapoint retrieval candidate lists and selected chunk IDs
- Include tie-break metadata in stored retrieval trace
- Add tests for ordering stability and artifact persistence

Definition of Done:
- Retrieval decisions are reproducible from stored artifacts
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-026 — C6: LLM Provider Adapter Normalization
Objective:
Normalize local/cloud provider response handling and deterministic schema parsing.

Scope:
- Refactor provider adapters into consistent response contract
- Improve error mapping for provider and schema failures
- Add adapter unit tests for valid/invalid payloads

Definition of Done:
- Local and cloud paths share stable extraction contract
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-027 — C7: Multi-Provider LLM Health Endpoint
Objective:
Expose deterministic health probes for both local and cloud providers.

Scope:
- Extend health endpoint to probe `local_lm_studio` and `openai_cloud`
- Return per-provider reachability + parse status
- Add tests with mocked transports

Definition of Done:
- Health endpoint gives actionable provider-level status
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-028 — C8: Ruleset Version Routing (Pre-2026 Support)
Objective:
Add deterministic ruleset selection for historical reporting periods.

Scope:
- Add routing logic for bundle/ruleset based on reporting year or range
- Preserve explicit override behavior
- Add tests for pre-2026 and post-2026 routing paths

Definition of Done:
- Historical runs can resolve applicable ruleset deterministically
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-029 — C9: Run Input Snapshot Freezing
Objective:
Freeze fully resolved run inputs for replay and audit reproducibility.

Scope:
- Persist immutable run input snapshot at execution start
- Include resolved datapoint universe and retrieval settings
- Add replay equivalence tests

Definition of Done:
- Run replay uses frozen inputs and reproduces output behavior
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-030 — C10: Failure Taxonomy + Retry Policy
Objective:
Standardize execution failure classes and deterministic retry semantics.

Scope:
- Introduce typed failure categories
- Add deterministic retry policy for retryable categories only
- Add tests for transitions and event logging

Definition of Done:
- Failure handling is explicit and test-covered
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-031 — D1: Report Data Model Refactor
Objective:
Move report generation onto typed DTOs with explicit denominator semantics.

Scope:
- Add typed report model
- Ensure coverage denominator/exclusions are explicit
- Update report generation tests/snapshots

Definition of Done:
- Report contract is explicit and deterministic
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-032 — D2: Report Preview API
Objective:
Provide in-app pre-download report preview payload.

Scope:
- Add preview endpoint returning rendered report + structured sections
- Preserve tenant scoping and run completion constraints
- Add API tests

Definition of Done:
- UI can preview report before download/export
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-033 — D3: Evidence Pack Preview API
Objective:
Provide deterministic preview of evidence pack contents before download.

Scope:
- Add endpoint listing evidence-pack files/checksums
- Validate preview matches ZIP manifest content
- Add integration tests

Definition of Done:
- Preview output and downloaded ZIP manifest are consistent
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-034 — D4: UI Step-State Hardening
Objective:
Stabilize frontend orchestration states and error handling for run setup.

Scope:
- Introduce explicit UI step-state transitions
- Improve user-visible errors for API failures
- Add frontend tests for stage transitions

Definition of Done:
- Setup flow avoids silent stalls/regressions
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-035 — D5: UI Discovery → Ingestion → Run Orchestration
Objective:
Wire discovery-driven flow into guided UI orchestration.

Scope:
- Connect company setup to discovery, ingestion, and run start
- Add deterministic progress stage updates
- Add frontend/API integration tests

Definition of Done:
- End-to-end guided flow works in local environment
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-036 — E1: Evidence-Gating Enforcement Audit Pass
Objective:
Enforce evidence gating invariants at persistence and verification boundaries.

Scope:
- Add hard guardrails rejecting Present/Partial without evidence IDs
- Extend tests for invariant enforcement and downgrade paths

Definition of Done:
- Evidence-gating invariant is enforced centrally and tested
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-037 — E2: Export Lifecycle Contract Hardening
Objective:
Eliminate export/report lifecycle edge cases (404/ambiguous readiness).

Scope:
- Standardize 409/404 semantics for report/evidence readiness
- Add deterministic readiness checks
- Add lifecycle integration tests

Definition of Done:
- Export/report endpoints return predictable contract states
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-038 — E3: Security and Secrets Baseline
Objective:
Finalize local security baseline for key/config handling.

Scope:
- Harden `.env` validation + startup fail-fast for required keys by provider
- Add sensitive log redaction checks
- Add tests for config validation and redaction

Definition of Done:
- Secrets handling baseline established and test-covered
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-039 — E4: CI Determinism Gates Expansion
Objective:
Expand CI checks for determinism-critical pathways.

Scope:
- Add CI jobs/subsets for chunking, retrieval ordering, run hash, report/export snapshots
- Validate migrations and workflow syntax in CI

Definition of Done:
- CI catches deterministic regressions earlier
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-040 — E5: UAT Harness and Golden Scenario Pack
Objective:
Ship reproducible UAT scenarios for local and cloud provider modes.

Scope:
- Add scenario fixtures and expected outputs
- Add harness checks for determinism and contract compliance
- Document operator runbook for UAT execution

Definition of Done:
- End-to-end UAT harness is reproducible and versioned
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-041 — F1: Persistence Architecture Lock (Postgres + pgvector)
Objective:
Lock persistence architecture to align implementation with ADR-0001 storage decisions.

Scope:
- Add ADR documenting Postgres + pgvector cutover and SQLite phase-out policy
- Define transitional policy: SQLite allowed only for tests/local transitional workflows
- Define deterministic SQL ordering requirements where row order is material
- Update conveyor plan/state context for cutover sequence

Definition of Done:
- Persistence cutover architecture is documented and accepted in-repo
- Test/documentation guards ensure ADR artifact remains present
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-042 — F2: Local Postgres/pgvector + MinIO Provisioning Baseline
Objective:
Provision deterministic local infrastructure for Postgres (with pgvector) and S3-compatible storage.

Scope:
- Harden `docker-compose.yml` for Postgres+pgvector and MinIO with health checks
- Add Postgres init SQL for `CREATE EXTENSION IF NOT EXISTS vector`
- Add Make targets: `compose-up`, `compose-down`, `db-wait`
- Add tests locking compose/make infra contract

Definition of Done:
- Local infrastructure can be brought up/down with make targets
- Postgres container initializes pgvector extension deterministically
- Tests pass

Tests:
- `make lint`
- `make test`
