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
Next PR ID: PR-003

Planned PRs:
- PR-000: Repo scaffold + agent memory files + PR template
- PR-001: Tooling + CI (lint/test), minimal `make` targets
- PR-002: Codex GitHub Action workflows + prompt files wired to PR review automation
- PR-003: Deterministic ingestion + chunk ID strategy implementation (planned)

## 4) Completed Work
- PR-000: Repo scaffold + governance context files + PR template/checklists + ADR-0001.
- PR-001: Tooling + CI baseline (`make lint`, `make test`), Python package scaffold, and deterministic run-fingerprint unit tests.
- PR-002: Added Codex GitHub Action workflows and prompt files for PR conveyor execution and automated PR review comments.

## 5) Open Risks / Unknowns
- GitHub secrets and permissions for Codex Action must be configured (OPENAI_API_KEY, etc.).
- Sample documents for deterministic tests: must be small and redistributable.
- Choice of PDF parsing stack: must be deterministic and testable; avoid fragile OCR in MVP.

## 6) Decisions Log (High Level)
- Start with Option 1: GitHub Actions + Codex GitHub Action for stable autonomy.
- Option 2 (Codex SDK orchestrator) will be evaluated after deterministic golden tests exist.

## 7) How to Update This File
Each PR must:
- Mark the PR as completed in section 4
- Update “Next PR ID”
- Add or resolve risks
- Record any new architectural decisions
