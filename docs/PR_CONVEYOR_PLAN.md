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

---

## PR-051 — Gold Standard Contract + Manifest Versioning
Objective:
Adopt `gold_standard_v1` report template contract and persist template version in manifest.

Scope:
- Add report contract reference and code constant `REPORT_TEMPLATE_VERSION = "gold_standard_v1"`
- Extend `run_manifest` persistence and APIs with `report_template_version`
- Add structural tests for deterministic section presence

Definition of Done:
- Manifest stores report template version
- Report rendering includes deterministic gold-standard section anchors
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-052 — Discovery Recall Upgrade (Year-Range + Multi-Query)
Objective:
Improve ESG document discovery recall for multi-year periods.

Scope:
- Query Tavily across reporting year range and merge deterministically
- Deterministic dedupe/tie-break for candidates
- Expand diagnostics for candidate funnel visibility

Definition of Done:
- Discovery considers year range and returns stable ordering
- Candidate funnel metrics available in response/logs
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-REG-001 — Regulatory Bundle Schema + DB Model + Migration
Objective:
Ensure DB-backed storage supports versioned bundle metadata and deterministic lifecycle management.

Scope:
- Extended `regulatory_bundle` model/migration with status + source-record metadata + unique `(regime,bundle_id,version)`.
- Added run-manifest regulatory context columns for compiler output persistence.

Definition of Done:
- Migration chain reaches head with new columns.
- Existing and new bundle workflows remain deterministic.

Tests:
- `make lint`
- `make test`

---

## PR-REG-002 — Bundle Loader + Sync Command (Repo JSON → DB)
Objective:
Provide deterministic repo-bundle sync with explicit `merge|sync` behavior.

Scope:
- Extended registry sync service to support `mode=merge|sync`.
- Added CLI: `python -m apps.api.app.scripts.sync_regulatory_bundles --path app/regulatory/bundles --mode sync`.

Definition of Done:
- Sync is deterministic and idempotent.
- `sync` mode deactivates bundles absent from source path.

Tests:
- `make lint`
- `make test`

---

## PR-REG-003 — Minimal EU Bundle (CSRD/ESRS Core)
Objective:
Ship a working EU-first core bundle for compiler context and report metadata.

Scope:
- Added `app/regulatory/bundles/csrd_esrs_core@2026.02.json`.
- Includes ESRS E1-1 and E1-6 obligations plus NO overlay example.
- Added bundle README.

Definition of Done:
- Bundle validates and compiles.
- Bundle sync includes new core bundle.

Tests:
- `make lint`
- `make test`

---

## PR-REG-004 — Regulatory Compiler v1
Objective:
Compile company context into deterministic applicable/excluded obligation plans.

Scope:
- Added `apps/api/app/services/regulatory_compiler.py`.
- Selects active bundles by company jurisdictions/regimes, applies overlays, and returns stable plan hash.

Definition of Done:
- Stable ordering/hash behavior for repeated runs.
- Overlay behavior deterministic by jurisdiction.

Tests:
- `make lint`
- `make test`

---

## PR-REG-005 — Persist Plan in Manifest + Report Metadata
Objective:
Eliminate `n/a` registry metadata by persisting compiler outputs and rendering them.

Scope:
- Run execution now persists registry version/compiler version/plan JSON/plan hash in `run_manifest`.
- Report metadata now renders manifest-backed values instead of placeholder `n/a`.
- Added `/runs/{run_id}/regulatory-plan` endpoint.

Definition of Done:
- Manifest contains persisted regulatory context.
- Report metadata displays real run context values.

Tests:
- `make lint`
- `make test`

---

## PR-REG-006 — Jurisdiction Overlay Framework
Objective:
Support overlay add/modify/disable logic in bundle schema/compiler.

Scope:
- Extended schema with `overlays[]`.
- Compiler applies overlay obligations for matching jurisdictions.
- Added NO overlay example in core bundle.

Definition of Done:
- NO+EU context includes overlay obligations.
- EU-only context excludes NO overlay obligations.

Tests:
- `make lint`
- `make test`

---

## PR-REG-007 — Coverage Matrix Assembly v1
Objective:
Keep obligation coverage matrix deterministic and renderable alongside report sections.

Scope:
- Coverage matrix helper supports explicit obligation-ID inclusion and deterministic ordering.
- Report metadata now includes obligations applied count from manifest plan.

Definition of Done:
- Matrix/report rendering deterministic with registry metadata context.

Tests:
- `make lint`
- `make test`

---

## PR-REG-008 — Regulatory Context Read APIs
Objective:
Expose read-only regulatory context for UI/ops diagnostics.

Scope:
- Added endpoints:
  - `GET /regulatory/sources?jurisdiction=EU`
  - `GET /regulatory/bundles?regime=CSRD_ESRS`
  - `GET /runs/{run_id}/regulatory-plan`

Definition of Done:
- Endpoints return deterministic ordered responses and pass auth/tenant checks.

Tests:
- `make lint`
- `make test`

---

## PR-053 — Download Robustness + PDF Validation
Objective:
Increase ingestion success for discovered candidates while keeping PDF-only MVP policy.

Scope:
- Replace URL-suffix-only filtering with fetch-time PDF validation
- Add deterministic retry + headers for hostile hosts
- Raise configurable document size limit for large ESG reports

Definition of Done:
- More candidate downloads succeed; failures are structured
- Non-PDF payloads are still blocked deterministically
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-054 — Duplicate Ingestion Correctness (Cross-Company)
Objective:
Prevent duplicate-hash ingestion from orphaning company document inventories.

Scope:
- Add deterministic company-document link model
- On duplicate hash, link existing canonical document to requesting company
- Update document hash and retrieval inputs to include linked documents

Definition of Done:
- Duplicate documents are accessible for new company runs
- No cross-company leakage; deterministic behavior preserved
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-055 — Retrieval Isolation + Ranking Quality
Objective:
Ensure run retrieval only uses run-company documents and keeps deterministic ranking.

Scope:
- Add company-scoped retrieval filtering
- Keep explicit tie-breaks and deterministic ordering
- Persist retrieval trace with source document ids

Definition of Done:
- Retrieval scope excludes unrelated tenant documents
- Ordering remains stable and test-covered
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-056 — Anti-Truncation Context Budgeting
Objective:
Protect analysis quality from silent context truncation.

Scope:
- Deterministic context budgeting metadata (`context_tokens`, `truncation_applied`)
- Explicit downgrade/fail-closed behavior when evidence context is truncated
- Add run diagnostics coverage for truncation flags

Definition of Done:
- Truncation is explicit, auditable, and tested
- No silent quality degradation path
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-057 — Gold Standard Renderer Mapping
Objective:
Map report generator sections to the gold standard template.

Scope:
- Deterministic assembly of metadata, applicability, inventory, coverage matrices, appendices
- Narrative placeholders constrained to validated facts only
- Keep evidence traceability appendix deterministic

Definition of Done:
- Output contains required gold-standard sections with deterministic ordering
- Tests validate structure and stable normalization

Tests:
- `make lint`
- `make test`

---

## PR-058 — Deterministic Rating Engine
Objective:
Compute compliance ratings from datapoint/obligation coverage, not free text.

Scope:
- Implement deterministic overall rating rules
- Surface rating in report summary section
- Add tests for Full/Partial/Absent/NA edge cases

Definition of Done:
- Ratings are rule-based and reproducible
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-059 — Side-by-Side A/B Benchmark Harness
Objective:
Operationalize local-vs-cloud benchmark runs with normalized outputs.

Scope:
- Add benchmark harness for predefined company/year ranges
- Produce side-by-side discovery and report quality metrics
- Persist normalized artifacts for regression review

Definition of Done:
- One command produces comparable A/B benchmark artifacts
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-060 — UI Quality Diagnostics
Objective:
Expose discovery and report-readiness quality diagnostics in the UI.

Scope:
- Add discovery funnel and skip-reason visibility
- Add report quality gates/warnings before download
- Preserve existing flow and deterministic API contracts

Definition of Done:
- Users can inspect failures pre-export from UI
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-061 — CI Regression Gates for Gold Standard
Objective:
Guard discovery/analysis/report quality with CI regression checks.

Scope:
- Add golden structure checks for report template sections
- Add deterministic benchmark threshold checks
- Integrate checks into CI workflow

Definition of Done:
- CI fails on structural/determinism regressions
- Tests pass

Tests:
- `make lint`
- `make test`

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

---

## PR-043 — F3: Postgres-First Local Defaults
Objective:
Switch local bootstrap defaults to Postgres while keeping explicit SQLite override support.

Scope:
- Update `.example.env` and Makefile development defaults to Postgres DSN
- Document explicit SQLite override for transitional/test use
- Add tests locking Postgres-first default contract

Definition of Done:
- Fresh local setup defaults to Postgres path
- SQLite is only used when explicitly configured
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-044 — F4: Postgres Migration Smoke Gates
Objective:
Validate Alembic migration lifecycle against Postgres in CI and local smoke tooling.

Scope:
- Add Postgres migration smoke test (upgrade/downgrade/upgrade)
- Add CI job running postgres migration smoke against service container
- Keep local `make test` deterministic with skip when Postgres URL is not provided

Definition of Done:
- Postgres migration regressions are caught automatically
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-045 — F5: pgvector Embedding Schema Activation
Objective:
Activate pgvector-backed embedding storage path while preserving compatibility.

Scope:
- Add migration for pgvector embedding column on Postgres
- Wire retrieval path to prefer vector column when available
- Add tests for retrieval stability with vector-backed payloads

Definition of Done:
- pgvector column exists in Postgres path and retrieval remains deterministic
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-046 — F6: Postgres End-to-End Harness
Objective:
Add deterministic end-to-end harness path against Postgres backend.

Scope:
- Add Postgres-mode E2E script/test for company->upload->run->report/evidence flow
- Validate run manifests, readiness contracts, and export behavior on Postgres
- Keep test gated for environments without Postgres service

Definition of Done:
- Postgres E2E flow is executable and test-covered
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-047 — F7: SQLite to Postgres Migration Tooling
Objective:
Provide deterministic migration utility from legacy SQLite datasets to Postgres.

Scope:
- Add migration CLI for core run/document/assessment/manifests/events tables
- Add count/hash verification report output
- Add unit tests for idempotent migration behavior

Definition of Done:
- Migration utility is deterministic and repeatable
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-048 — F8: Dual-Backend Determinism Parity Checks
Objective:
Compare SQLite and Postgres outputs for deterministic parity during transition.

Scope:
- Add parity harness for key artifacts (manifest/report/evidence metadata)
- Add normalization strategy for non-deterministic fields
- Add regression tests for parity contract

Definition of Done:
- Drift between backends is detectable and test-covered
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-049 — F9: Postgres SoR Runtime Cutover
Objective:
Make Postgres the enforced system-of-record runtime backend.

Scope:
- Update runtime defaults/config checks to reject SQLite in non-test modes
- Add explicit transitional override flag for controlled dev/test usage
- Add tests for runtime enforcement behavior

Definition of Done:
- Runtime defaults enforce Postgres system-of-record policy
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-050 — F10: SQLite Phase-Down and Final Validation
Objective:
Complete transition by phasing down SQLite from primary runbooks and validating full flow.

Scope:
- Update runbooks/make docs to mark SQLite as transitional/test-only
- Add final Postgres flow validation checklist and operator guidance
- Add final transition guard tests

Definition of Done:
- Repo guidance reflects Postgres-first operation and SQLite phase-down
- Tests pass

Tests:
- `make lint`
- `make test`

---

## PR-REG-009 — Registry Compiler Activation and Relational Plan Persistence
Objective:
Upgrade from manifest-only compiled context to a first-class persisted compiled plan model with strict run guardrails.

Scope:
- Add relational persistence for compiled plans and obligations:
- `compiled_plan` (`id`, `entity_id`, `reporting_year`, `regime`, `cohort`, `phase_in_flags`, `created_at`)
- `compiled_obligation` (`id`, `compiled_plan_id`, `obligation_code`, `mandatory`, `jurisdiction`)
- Wire compiler output to persist both relational tables plus existing manifest fields
- Make `run_manifest.regulatory_plan_id` required for new runs (migration + runtime enforcement)
- Add run bootstrap guard: fail execution when in-scope CSRD entity compiles to zero obligations

Definition of Done:
- Every successful run references a persisted `regulatory_plan_id`
- No `n/a` registry metadata for compiler-enabled runs
- In-scope CSRD run produces `compiled_obligation > 0` or fails deterministically with explicit reason

Tests:
- `make lint`
- `make test`

---

## PR-REG-010 — Document Universe and Deterministic Inventory Engine
Objective:
Establish deterministic document inventory independent of extraction/analysis.

Scope:
- Add document universe service (`document_universe`) that builds normalized inventory records from upload/discovery sources
- Add deterministic regex-based classification (`annual report`, `sustainability`, `transparency act`, `slavery`, `pillar 3`, `factbook`)
- Persist inventory fields on document records (or linked table): `doc_type`, `reporting_year`, `source_url`, checksum, classification confidence
- Add inventory API response/UI rendering contract:
- Table renders before extraction starts
- Empty state: `No documents discovered`

Definition of Done:
- Inventory renders with deterministic classification for discovered/uploaded documents
- Inventory availability is decoupled from datapoint extraction progress

Tests:
- `make lint`
- `make test`

---

## PR-REG-011 — Retrieval/Verification Contract Hardening
Objective:
Enforce evidence contract with structured diagnostics and explicit failure codes.

Scope:
- Add persisted extraction diagnostics payload per datapoint:
- `retrieved_chunk_ids`, `retrieved_chunk_lengths`, `numeric_matches_found`, `verification_status`
- `failure_reason_code` enum (`CHUNK_NOT_FOUND`, `EMPTY_CHUNK`, `NUMERIC_MISMATCH`, `BASELINE_MISSING`)
- Enforce pre-Present contract:
- every cited chunk exists
- every cited chunk has non-empty text
- otherwise downgrade deterministically to `Absent`
- Add synthetic fixture regression to assert orphan cited chunks cannot pass verification

Definition of Done:
- No orphan evidence chunk IDs survive as `Present/Partial`
- Diagnostics are queryable and stable for each datapoint execution

Tests:
- `make lint`
- `make test`

---

## PR-REG-012 — Metric Datapoint Type System
Objective:
Introduce typed metric datapoints with baseline-aware validation.

Scope:
- Extend datapoint schema with `type` (`narrative|metric`) and `requires_baseline`
- Add metric extraction contract:
- `value`, `unit`, `year`, optional baseline year/value, `source_chunk_id`
- Add deterministic numeric pre-parser (percent, currency, tCO2e, bn/million multipliers)
- Add downgrade rules:
- percentage without baseline -> downgrade
- missing year -> downgrade
- unit mismatch -> downgrade

Definition of Done:
- Metric datapoints populate structured quantitative fields
- Baseline-required metrics enforce downgrade semantics deterministically

Tests:
- `make lint`
- `make test`

---

## PR-REG-013 — Obligation Coverage Matrix Persistence and Rendering
Objective:
Make obligation-level coverage a persisted first-class output.

Scope:
- Add obligation coverage aggregation service:
- `Full` = all mandatory datapoints Present
- `Partial` = at least one Present but not all
- `Absent` = none Present
- Persist matrix rows in `obligation_coverage` keyed by `compiled_plan_id`
- Render matrix sections deterministically (`Cross-cutting`, `E1`, `S1`, `G1`) even for sparse datapoints

Definition of Done:
- Matrix is never empty for non-empty compiled plans
- Matrix results are independent of report narrative generation

Tests:
- `make lint`
- `make test`

---

## PR-REG-014 — Run Orchestration Guardrails
Objective:
Add explicit pre-run and in-run integrity guardrails to prevent false-complete outcomes.

Scope:
- Add run preflight checks:
- compiled plan missing -> abort
- document universe empty -> warn + continue
- chunk table empty -> abort extraction stage
- Add diagnostics threshold policy:
- if diagnostics failure rate exceeds threshold, set run status `integrity_warning` (or equivalent deterministic terminal subtype)
- Persist guardrail outcomes in run events and diagnostics payload

Definition of Done:
- Runs cannot silently complete without core prerequisites
- Guardrail decisions are visible in status/diagnostics APIs and UI

Tests:
- `make lint`
- `make test`

---

## PR-REG-015 — Discovery Recall and Source Ranking Uplift (Planned)
Objective:
Improve deterministic discovery recall/precision for ESG filing retrieval while preserving reproducibility.

Scope (planned):
- Expand deterministic search query templates by filing taxonomy and period.
- Add source-ranking policy with explicit tie-breaks and provenance metadata.
- Add benchmark fixtures and acceptance gates for recall/precision drift.

Definition of Done:
- Deterministic discovery benchmark improves document recall on reference fixtures.
- All ranking/tie-break behavior remains explicit and test-covered.

Tests:
- `make lint`
- `make test`

---

## PR-NBLM-000 — ADR: NotebookLM MCP Regulatory Research Service (Completed)
Objective:
Formalize NotebookLM as workflow-only research support with explicit scoring isolation.

Scope:
- Add ADR documenting usage boundaries, non-goals, governance, and breakage handling.
- Include rollout notebook reference and kill-switch requirement.

Definition of Done:
- ADR states: no scoring-path dependency on NotebookLM.
- ADR states: integration is behind feature flags + kill switch.
- ADR includes clear disable/fallback breakage plan.

---

## PR-NBLM-001 — Research Provider Interface + Orchestrator (Completed)
Objective:
Add provider-agnostic research abstraction with deterministic request hashing.

Scope:
- Add request/response/citation types.
- Add provider interface.
- Add research service orchestrator with provider injection.
- Add unit tests for hash determinism and service pass-through behavior.

Definition of Done:
- New research modules compile and tests pass.
- No scoring modules import research package.

---

## PR-NBLM-002 — Feature Flags + Kill Switch (Completed)
Objective:
Add safe-default feature controls with deterministic disabled behavior.

Scope:
- Add `FEATURE_REG_RESEARCH_ENABLED`, `FEATURE_NOTEBOOKLM_ENABLED`, strict-citation, persist, fail-open, and cache TTL settings.
- Service returns deterministic stub response when disabled.
- Document flags in README/.example env.

Definition of Done:
- Default configuration performs no external calls.
- Disabled mode returns deterministic `stub` response.

---

## PR-NBLM-003 — Citation Validation Policy (Completed)
Objective:
Enforce citation quality contract before any persistence path.

Scope:
- Add citation validator with strict/non-strict modes.
- Add typed citation validation error.
- Wire validator into research service.
- Add tests for strict reject/non-strict persist gating.

Definition of Done:
- Strict mode rejects empty/invalid citations.
- Non-strict mode allows responses but blocks persistence when citation quality is insufficient.

---

## PR-NBLM-004 — DB-Backed Research Cache (Completed)
Objective:
Add deterministic request-response caching in Postgres.

Scope:
- Migration + model for `regulatory_research_cache`.
- Cache repo with read-through and TTL behavior.
- Service cache-hit short-circuit and failure caching.
- Tests for hit/miss/failure paths.

Definition of Done:
- Cache hit bypasses provider call.
- Success and failure outcomes are persisted with TTLs.

---

## PR-NBLM-005 — Requirement-Linked Research Notes (Completed)
Objective:
Persist additive research notes linked to requirements without mutating canonical requirement records.

Scope:
- Migration + model for `regulatory_requirement_research_notes`.
- Notes repo and service method `query_and_maybe_persist`.
- Feature-flag and citation-gated persistence behavior.
- Tests for enabled/disabled persistence and citation enforcement.

Definition of Done:
- Notes are persisted only when enabled and citations allow persistence.
- Canonical requirement content is not auto-mutated.

---

## PR-NBLM-006 — NotebookLM Provider Adapter (Completed)
Objective:
Implement concrete NotebookLM MCP provider adapter wiring into `ResearchProvider`.

Scope:
- Added HTTP JSON-RPC MCP client with timeout/retry controls and typed error handling.
- Added NotebookLM provider implementation with corpus-key notebook resolution and ordered tool calls.
- Added citation parser for trailing `CITATIONS:` markdown block.
- Added tests for MCP retry behavior, provider call order, parser extraction, and default notebook mapping.

Definition of Done:
- Provider can be injected into `RegulatoryResearchService`.
- Default notebook mapping includes `EU-CSRD-ESRS -> 7bbf7d0b-db30-488e-8d2d-e7cbad3dbbe5`.
- Errors are typed and workflow-safe.

Tests:
- `make lint`
- `make test`

---

## PR-NBLM-007 — Provider Wiring Endpoint/CLI (Planned)
Objective:
Expose an internal API/CLI path to exercise NotebookLM research queries using feature-flag gates.

Tests:
- `make lint`
- `make test`

---

## PR-NBLM-008 — Research Observability + Audit Events (Planned)
Objective:
Add deterministic event/audit records for research requests, cache hits, validation outcomes, and failures.

Tests:
- `make lint`
- `make test`

---

## PR-NBLM-009 — NotebookLM Health Probe + Diagnostics (Planned)
Objective:
Add MCP/provider health probing with actionable diagnostics and non-fatal workflow behavior.

Tests:
- `make lint`
- `make test`

---

## PR-NBLM-010 — UI/Workflow Research Assist Hooks (Planned)
Objective:
Add internal workflow hooks to request and view requirement-linked research notes without touching scoring paths.

Tests:
- `make lint`
- `make test`
