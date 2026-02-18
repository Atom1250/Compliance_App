# PROJECT_STATE.md — Compliance App (Live Context)

This file is the single source of truth for project status and decisions-in-progress.
Every PR MUST update this file.

## 0) Project Summary
We are building a compliance analysis application for EU clients:
- CSRD/ESRS compliance and gap reporting
- Green finance alignment (ICMA Green Bond Principles, EU Green Bond Standard / EuGB)
- Deterministic, evidence-gated results with citations + evidence pack exports
- RAG-based retrieval to reduce tokens and increase speed
- Local LLM used for structured extraction; external services only for optional web search in later phases

## 1) Architectural Snapshot (Current)
- Backend: FastAPI (planned)
- Worker: background job runner (planned)
- DB: Postgres + pgvector (planned)
- Object storage: S3-compatible (MinIO in dev; planned)
- Frontend: Next.js (planned; later)
- Requirements Library: versioned bundles stored in repo and imported into DB
- Determinism: strict (stable chunk IDs, retrieval tie-breaks, schema-only LLM outputs, run-hash caching)

## 2) Non-Negotiables
- Requirements-first / datapoint-native / evidence gating
- Run manifest + reproducible outputs
- No implicit global state (no env-based run context)
- CI gates merges; all PRs must add tests

## 3) PR Conveyor Index
Next PR ID: TBD

Planned PRs:
- TBD: roadmap currently exhausted after PR-082 and PR-090.

## 4) Completed Work
- PR-000: Repo scaffold + governance context files + PR template/checklists + ADR-0001.
- PR-001: Tooling + CI baseline (`make lint`, `make test`), Python package scaffold, and deterministic run-fingerprint unit tests.
- PR-002: Added Codex GitHub Action workflows and prompt files for PR conveyor execution and automated PR review comments.
- PR-001 and PR-002 are merged to `main` and active in repository workflows/tooling.
- PR-003: Conveyor normalization and deterministic ingestion baseline completed:
  - Added canonical roadmap scope section for PR-003 in `docs/PR_CONVEYOR_PLAN.md`.
  - Normalized ADR path with `docs/adr/0001-architecture.md`.
  - Added deterministic document identity helpers (`sha256_bytes`, `stable_document_id`) with explicit input contracts.
  - Added deterministic unit tests for stable and changed document hash/identity behavior.
- PR-010: FastAPI skeleton + configuration layer completed:
  - Added FastAPI app entrypoint at `apps/api/main.py` with app package structure under `apps/api/app/`.
  - Added `/healthz` and `/version` routes via `api/routers/` and environment-driven config in `core/config.py`.
  - Added Pydantic settings model (`COMPLIANCE_APP_` env prefix) and wired app metadata/version deterministically.
  - Added tests for health endpoint and env-backed version/config loading.
- PR-011: Postgres schema + migrations completed:
  - Added Postgres docker-compose service (`docker-compose.yml`) and database URL wiring in settings.
  - Added SQLAlchemy ORM models and DB session management for `company`, `document`, `document_file`, `run`, and `run_event`.
  - Added Alembic configuration and initial migration for the required schema.
  - Added migration idempotency and CRUD integration tests (`company` + `run`) against a test database.
- PR-012: Object storage + document upload completed:
  - Added MinIO service to `docker-compose.yml` for S3-compatible local object storage in dev.
  - Implemented `POST /documents/upload` to store original bytes, compute SHA-256, and deduplicate stored objects by hash.
  - Added metadata persistence linking uploaded document records to deterministic storage URIs.
  - Added document metadata retrieval endpoint and integration test covering upload, retrieval, and duplicate-upload same-reference behavior.
- PR-020: Page-level extraction completed:
  - Added deterministic PDF and basic DOCX extraction service with parser-version metadata per extracted page.
  - Added `document_page` schema via migration and ORM model to persist `page_number`, `text`, `char_count`, and `parser_version`.
  - Wired document upload flow to extract and persist page rows after immutable object storage.
  - Added determinism tests showing repeated extraction/storage on a fixed PDF yields identical persisted page snapshots.
- PR-021: Deterministic chunking + pgvector baseline completed:
  - Added deterministic chunking service with fixed chunk-size/overlap rules and stable chunk IDs derived from `document_hash + page + offsets`.
  - Added `chunk` and `embedding` tables plus Alembic migration with pgvector extension bootstrap for PostgreSQL environments.
  - Added FTS-ready `content_tsv` column and persistence wiring to generate chunks from extracted document pages during upload.
  - Added chunk determinism and retrieval-sanity tests with explicit stable tie-break behavior.
- PR-022: Hybrid retrieval engine completed:
  - Added deterministic hybrid retrieval service combining lexical and vector similarity with explicit weighted scoring.
  - Implemented stable tie-break ordering by `chunk_id` when combined scores are equal.
  - Added structured retrieval API endpoint (`POST /retrieval/search`) returning typed retrieval result records.
  - Added ordering determinism tests validating repeatable ranking and tie-break behavior.
- PR-030: Requirements bundle system completed:
  - Added `requirements/` bundle structure with sample `requirements/esrs_mini/bundle.json`.
  - Added requirements DB tables (`requirement_bundle`, `datapoint_def`, `applicability_rule`) via migration.
  - Implemented validated importer CLI (`python -m app.requirements import`) and import service.
  - Added tests for import success, idempotency, and version pin behavior.
- PR-031: Company scope + applicability logic completed:
  - Added company profile fields (`employees`, `turnover`, `listed_status`, `reporting_year`) with DB migration support.
  - Implemented deterministic applicability engine to evaluate bundle rules against explicit company profile values.
  - Added deterministic output behavior with stable ordering for required datapoint IDs.
  - Added fixture-based unit tests validating expected datapoint applicability results.
- PR-032: Materiality questionnaire integration completed:
  - Added questionnaire endpoints for per-run topic materiality storage and required datapoint resolution.
  - Added persistent run-level topic decisions via `run_materiality` storage and DB migration support.
  - Integrated materiality filtering into applicability evaluation with deterministic ordering.
  - Added fixture-based tests confirming toggling materiality changes required datapoints.
- PR-040: LLM client + schema enforcement completed:
  - Added deterministic OpenAI-compatible LLM extraction client abstraction with enforced `temperature=0`.
  - Defined strict extraction JSON schema (`status`, `value`, `evidence_chunk_ids`, `rationale`) with schema-only parsing.
  - Implemented hard evidence gating validation rejecting Present/Partial without evidence IDs.
  - Added mock-based extraction tests for temperature enforcement, schema validation, and evidence gating behavior.
- PR-041: Datapoint assessment pipeline completed:
  - Added deterministic retrieval -> extraction -> persistence pipeline for required datapoints.
  - Added `datapoint_assessment` storage schema with run/datapoint uniqueness and manifest metadata fields.
  - Persisted extraction provenance per assessment (`model_name`, `prompt_hash`, deterministic `retrieval_params`).
  - Added mocked integration test validating stored assessment outputs and deterministic manifest fields.
- PR-042: Verification pass completed:
  - Added deterministic post-extraction verification checks for cited numeric values, units, and year/period signals.
  - Implemented predictable downgrade rules (`Present -> Partial`, `Partial -> Absent`) when verification fails.
  - Integrated verification into the assessment pipeline prior to persistence.
  - Added crafted edge-case tests for numeric mismatch, missing evidence chunks, and year consistency failures.
- PR-043: Run hashing + cache completed:
  - Added deterministic run hash computation from document hashes, company profile, materiality inputs, bundle version, retrieval params, and prompt hash.
  - Added persistent run cache storage (`run_cache_entry`) for run-hash keyed output reuse.
  - Implemented cache-first execution helper returning cached output and skipping recomputation on hash hit.
  - Added deterministic tests for run hash stability/input sensitivity and cache-hit behavior with identical output reuse.
- PR-050: Deterministic HTML report generator completed:
  - Added deterministic HTML report renderer with executive summary, coverage metrics, gap summary, and datapoint table.
  - Added inline citation references in datapoint rows using evidence chunk IDs.
  - Added timestamp normalization utility for stable snapshot testing.
  - Added snapshot-style and repeatability tests to verify byte-stable normalized HTML output for identical inputs.
- PR-051: Evidence pack ZIP export completed:
  - Added deterministic ZIP exporter producing `manifest.json`, `assessments.jsonl`, `evidence.jsonl`, and referenced document binaries.
  - Added stable entry ordering and fixed ZIP metadata timestamps to ensure reproducible archives for identical inputs.
  - Added document integrity validation by re-hashing referenced document bytes against stored `sha256_hash`.
  - Added manifest integrity test validating file structure and SHA-256 checks for all packed artifacts.
- PR-052: Optional PDF export completed:
  - Added optional PDF export service to convert HTML reports into PDF bytes.
  - Added explicit feature flag behavior so PDF generation is skipped when disabled.
  - Added graceful dependency-missing error handling for environments without PDF renderer libraries.
  - Added unit tests for disabled mode, enabled export path, and dependency-missing behavior.
- PR-060: Green finance requirements bundle completed:
  - Added a versioned green finance requirements bundle for ICMA GBP + EuGB alignment.
  - Added obligation metadata (required artifacts and required data elements) for matrix rendering.
  - Implemented deterministic obligations matrix generation with output fields: obligation, required, produced, evidence, gap.
  - Added tests for bundle loading, enabled-mode matrix generation, and disabled-mode suppression.
- PR-061: Green finance extraction pipeline completed:
  - Added green finance extraction pipeline that reuses the existing deterministic datapoint assessment engine.
  - Implemented retrieval + schema-enforced extraction flow for green finance obligations via the green finance requirements bundle.
  - Added reporting matrix generation directly from extracted assessments with evidence gating aligned to ESRS rules.
  - Added integration tests for enabled pipeline execution (stored assessments + reported matrix) and disabled-mode no-op behavior.
- PR-070: Minimal Next.js UI completed:
  - Added a minimal Next.js app scaffold under `apps/web` with a deterministic operational flow.
  - Implemented required pages: company setup, upload docs, run configuration, run status, and report download.
  - Added shared API client integration used across workflow pages with graceful local fallbacks for unavailable endpoints.
  - Added CI-visible scaffold tests validating required pages and shared API-client wiring.
- PR-080: API key auth + tenant isolation completed:
  - Added API key authentication dependency using request headers (`X-API-Key`, `X-Tenant-ID`) with tenant-aware key validation.
  - Added tenant isolation columns and indexes for core entity roots (`company`, `document`, `run`) with migration support.
  - Enforced tenant-scoped filtering in document, run/materiality, and retrieval API paths.
  - Added tests validating unauthorized access blocking and cross-tenant data isolation behavior.
- PR-090: Golden run + contract tests completed:
  - Added golden fixture document under `tests/fixtures/golden/` for deterministic contract validation.
  - Added golden snapshot harness producing deterministic output contract fields (hashes, chunk IDs, ranking, report snapshot).
  - Added committed snapshot artifact under `tests/golden/` and drift test that fails CI when output changes.
  - Added repeatability test confirming identical golden-run outputs across repeated execution.
- PR-082: Structured logging + audit trail completed:
  - Added structured JSON logging helper for deterministic audit log payloads.
  - Added run-event audit service to append and list ordered run history entries.
  - Added tenant-scoped run-events API endpoint (`GET /runs/{run_id}/events`) and persisted run events from materiality/required-datapoints workflows.
  - Added audit trail tests covering event ordering/completeness and tenant isolation.

## 5) Open Risks / Unknowns
- GitHub secrets and permissions for Codex Action must be configured (OPENAI_API_KEY, etc.).
- Sample documents for deterministic tests: must be small and redistributable.
- Choice of PDF parsing stack: must be deterministic and testable; avoid fragile OCR in MVP.
- Manual check still required in GitHub Actions UI to confirm `Codex Run Prompt (Create PR)` appears and dispatches with repository secrets.
- Tenant key management/rotation process is not yet documented; current baseline relies on environment configuration.

## 6) Decisions Log (High Level)
- Start with Option 1: GitHub Actions + Codex GitHub Action for stable autonomy.
- Option 2 (Codex SDK orchestrator) will be evaluated after deterministic golden tests exist.

## 7) How to Update This File
Each PR must:
- Mark the PR as completed in section 4
- Update “Next PR ID”
- Add or resolve risks
- Record any new architectural decisions
