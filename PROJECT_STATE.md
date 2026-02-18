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
Next PR ID: PR-030

Planned PRs:
- PR-030: Requirements bundle system (planned)

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

## 5) Open Risks / Unknowns
- GitHub secrets and permissions for Codex Action must be configured (OPENAI_API_KEY, etc.).
- Sample documents for deterministic tests: must be small and redistributable.
- Choice of PDF parsing stack: must be deterministic and testable; avoid fragile OCR in MVP.
- Manual check still required in GitHub Actions UI to confirm `Codex Run Prompt (Create PR)` appears and dispatches with repository secrets.

## 6) Decisions Log (High Level)
- Start with Option 1: GitHub Actions + Codex GitHub Action for stable autonomy.
- Option 2 (Codex SDK orchestrator) will be evaluated after deterministic golden tests exist.

## 7) How to Update This File
Each PR must:
- Mark the PR as completed in section 4
- Update “Next PR ID”
- Add or resolve risks
- Record any new architectural decisions
