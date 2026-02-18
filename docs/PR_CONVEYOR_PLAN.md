PR_CONVEYOR_PLAN.md
Compliance App — Implementation Roadmap (Phase B Onward)
This document defines the authoritative PR conveyor from PHASE B forward.
Codex must treat this as the long-horizon roadmap.
For each PR:
Implement ONLY the scope described.
Follow AGENTS.md invariants.
Update PROJECT_STATE.md.
Add/modify ADRs if architecture changes.
Ensure determinism and test coverage.
Do not implement future PR scope early.

## PR-003 — Conveyor Normalization + Deterministic Ingestion Baseline
Objective
Unblock autonomous PR execution by aligning roadmap/state references and add a minimal deterministic ingestion baseline.
Scope
- Add this PR-003 section so `Next PR ID: PR-003` has an authoritative scope.
- Normalize ADR file path references by ensuring `docs/adr/0001-architecture.md` exists.
- Add deterministic ingestion scaffolding only (no database or API expansion yet):
  - Pure helper(s) for deterministic document identity/hash handling.
  - Stable function contracts with explicit inputs (no global run state).
- Add/adjust tests for deterministic behavior added in this PR.
- Keep changes narrow; do not start PR-010 backend skeleton work.
Definition of Done
- `PROJECT_STATE.md` can resolve PR-003 to this section.
- `docs/adr/0001-architecture.md` is present and readable.
- Deterministic ingestion helper tests pass and are repeatable.
Tests
- Unit tests validating deterministic outputs for identical inputs.
- Negative test showing changed input changes deterministic identifier/hash.

PHASE B — Backend Core (API + DB + Storage)
PR-010 — FastAPI Skeleton + Configuration Layer
Objective
Create the minimal backend service foundation.
Scope
Create FastAPI app in apps/api/.
Add:
/healthz
/version
Add configuration system:
Pydantic-based settings class
Environment-variable driven
Add basic project structure:
app/ package
api/routers/
core/config.py
Ensure OpenAPI schema is auto-generated.
Definition of Done
uvicorn apps.api.main:app runs.
/healthz returns 200.
At least one unit test verifies health endpoint.
Tests
pytest test for health endpoint.
Config loads from env.
PR-011 — Postgres Schema + Migrations
Objective
Establish database system-of-record.
Scope
Add Docker Compose service for Postgres.
Add Alembic migrations.
Create initial tables:
company
document
document_file
run
run_event
Add DB session management.
Definition of Done
alembic upgrade head works.
CRUD test for company + run passes.
Tests
Integration test using test DB.
Ensure migrations idempotent.
PR-012 — Object Storage + Document Upload
Objective
Add immutable document ingestion.
Scope
Add MinIO service to docker-compose.
Create upload endpoint:
Store original bytes.
Compute SHA-256 hash.
Prevent duplicate storage by hash.
Create document metadata record linking to storage URI.
Definition of Done
Upload endpoint works.
File hash stored and verified.
Duplicate upload returns same stored reference.
Tests
Upload + retrieval integration test.
PHASE C — Deterministic Parsing + Retrieval
PR-020 — Page-Level Extraction
Objective
Convert uploaded documents into deterministic page records.
Scope
Implement PDF page extraction.
Store per-page text:
page_number
text
char_count
Record parser version in metadata.
Support DOCX text extraction (basic).
Definition of Done
Given sample PDF, pages are stored.
Re-running produces identical results.
Tests
Determinism test on fixed PDF sample.
PR-021 — Deterministic Chunking + pgvector
Objective
Create stable chunk IDs and embedding storage.
Scope
Implement chunker:
Stable chunk IDs = hash(doc_hash + page + offsets)
Fixed chunk size rules
Add pgvector extension.
Store:
chunk table
embedding table
tsvector column for FTS
Definition of Done
Same document → same chunk IDs.
Embeddings stored.
Tests
Chunk determinism test.
Retrieval sanity test.
PR-022 — Hybrid Retrieval Engine
Objective
Implement deterministic retrieval layer.
Scope
Hybrid retrieval:
Full-text search
Vector similarity
Deterministic score combination formula.
Stable tie-break ordering.
Definition of Done
Same query → same ordering.
Retrieval API returns structured results.
Tests
Ordering determinism test.
PHASE D — Requirements Library + Applicability Engine
PR-030 — Requirements Bundle System
Objective
Introduce versioned compliance requirements.
Scope
Add requirements/ directory structure.
Define bundle schema:
datapoint_def
applicability_rule
disclosure_reference
Create importer CLI:
python -m app.requirements import
DB tables:
requirement_bundle
datapoint_def
applicability_rule
Definition of Done
Sample ESRS mini-bundle imports successfully.
Bundle version stored in DB.
Tests
Import idempotency.
Version pin test.
PR-031 — Company Scope + Applicability Logic
Objective
Determine which datapoints apply to a company.
Scope
Add company profile fields:
employees
turnover
listed status
reporting_year
Implement applicability engine:
Evaluate rules deterministically.
Return required datapoint IDs.
Definition of Done
Given company profile fixture, expected datapoints returned.
Tests
Rule evaluation unit tests.
PR-032 — Materiality Questionnaire Integration
Objective
Incorporate structured double-materiality inputs.
Scope
Add questionnaire endpoints.
Store topic materiality per run.
Integrate with applicability engine.
Definition of Done
Toggling materiality changes required datapoints.
Tests
Fixture-based materiality tests.
PHASE E — LLM Extraction + Verification
PR-040 — LLM Client + Schema Enforcement
Objective
Add deterministic, schema-only LLM extraction.
Scope
Implement LLM client abstraction:
OpenAI-compatible API
temperature=0 enforced
Define JSON schema:
status
value
evidence_chunk_ids
rationale
Hard validation:
Reject Present without evidence.
Definition of Done
Mock LLM test passes.
Schema validation enforced.
Tests
Schema validation tests.
Evidence gating test.
PR-041 — Datapoint Assessment Pipeline
Objective
Implement full retrieval → extraction → storage loop.
Scope
For each required datapoint:
Retrieve top chunks.
Call LLM extractor.
Store assessment.
Record:
model name
prompt hash
retrieval parameters
Definition of Done
End-to-end sample run produces stored assessments.
Tests
Mocked LLM integration test.
PR-042 — Verification Pass
Objective
Add post-extraction consistency checks.
Scope
Validate numeric values appear in cited chunks.
Unit sanity checks.
Period/year sanity checks.
Ability to downgrade status if verification fails.
Definition of Done
Verification logic modifies invalid assessments predictably.
Tests
Crafted edge-case tests.
PR-043 — Run Hashing + Cache
Objective
Guarantee reproducibility.
Scope
Compute run hash from:
document hashes
company profile
materiality inputs
bundle version
retrieval params
prompt hash
If identical run exists:
Return stored results.
Skip reprocessing.
Definition of Done
Identical inputs produce identical output JSON.
Tests
Cache hit test.
PHASE F — Reporting + Evidence Pack
PR-050 — Deterministic HTML Report Generator
Objective
Generate structured compliance report.
Scope
HTML report with:
Executive summary
Coverage metrics
Gap summary
Datapoint table
Inline citation references.
Definition of Done
HTML stable across identical runs.
Tests
Snapshot test (timestamp normalized).
PR-051 — Evidence Pack ZIP Export
Objective
Produce audit-grade export.
Scope
ZIP containing:
manifest.json
assessments.jsonl
evidence.jsonl
referenced documents
Ensure evidence hash integrity.
Definition of Done
ZIP reproducible for identical runs.
Tests
Validate manifest structure and integrity.
PR-052 — Optional PDF Export (Feature-Flagged)
Objective
Add PDF rendering layer.
Scope
Convert HTML report to PDF.
Feature flag if dependencies missing.
Definition of Done
PDF generated in containerized test environment.
PHASE G — Green Finance Module
PR-060 — Green Finance Requirements Bundle
Objective
Add ICMA GBP + EuGB obligations matrix.
Scope
Create green finance bundle:
Obligations
Required artifacts
Required data elements
Matrix output structure:
Obligation
Required
Produced?
Evidence
Gap
Definition of Done
Matrix generated when green finance mode enabled.
PR-061 — Green Finance Extraction Pipeline
Objective
Reuse datapoint engine for green finance.
Scope
Retrieval + extraction for obligations.
Evidence gating identical to ESRS.
Definition of Done
Green finance assessments stored and reported.
PHASE H — Frontend
PR-070 — Minimal Next.js UI
Objective
Provide operational interface.
Scope
Pages:
Company setup
Upload docs
Run configuration
Run status
Report download
API client integration.
Definition of Done
End-to-end happy path works.
PHASE I — Security + Audit Hardening
PR-080 — API Key Auth + Tenant Isolation
Objective
Add multi-tenant security baseline.
Scope
API key auth.
Tenant isolation in DB queries.
Definition of Done
Unauthorized access blocked.
PR-082 — Structured Logging + Audit Trail
Objective
Harden run traceability.
Scope
Structured logs.
Complete run event history.
PHASE J — Regression Harness
PR-090 — Golden Run + Contract Tests
Objective
Lock determinism.
Scope
Add golden sample documents.
Snapshot expected outputs.
CI fails on output drift.
Definition of Done
Identical run → identical output snapshot.
PHASE K — Operations Hardening
PR-100 — Tenant Key Management + Rotation Runbook
Objective
Operationalize tenant API key lifecycle with auditable rotation.
Scope
Add tenant key management runbook:
Key generation
Rotation cadence
Revocation procedure
Document required environment variable format and examples.
Add validation utility:
Checks auth key config format at startup.
Fails fast on invalid tenant:key mappings.
Definition of Done
Tenant key lifecycle is documented and configuration validation prevents malformed key maps.
Tests
Unit tests for valid/invalid tenant key configuration parsing and validation.
PR-110 — Run Lifecycle API Endpoints
Objective
Complete API support for run creation and workflow status/report retrieval.
Scope
Add run lifecycle endpoints:
POST /runs (create queued run for tenant-scoped company)
GET /runs/{run_id}/status
GET /runs/{run_id}/report
Enforce tenant isolation on all run lifecycle routes.
Record structured audit events for lifecycle actions.
Definition of Done
Lifecycle endpoints provide deterministic responses and tenant-scoped access controls.
Tests
Integration tests for create/status/report happy path and cross-tenant denial.
END OF ROADMAP
