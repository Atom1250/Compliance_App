# AGENTS.md — Codex Operating Manual (Compliance App)

This repo is built to be developed autonomously by Codex in small PRs with strong guardrails.
All contributors (human or agent) MUST follow these rules.

## 1) Prime Objective
Build a Compliance App that:
- Assesses EU company disclosure compliance for CSRD/ESRS and green finance (ICMA GBP, EU Green Bond Standard / EuGB).
- Produces deterministic results: same inputs + same config => same outputs.
- Provides evidence-grade citations and an exportable evidence pack containing all supporting snippets and source documents.
- Minimizes token usage via RAG and structured extraction (no “free-form” analysis over full documents).

## 2) Architectural Invariants (Non-Negotiable)
1. **Requirements-first**: The app does not “infer requirements” from narrative. Requirements come from a versioned, curated Requirements Library bundle.
2. **Datapoint-native**: Compliance is evaluated at the datapoint level (Present / Partial / Absent / NA) with explicit evidence IDs.
3. **Evidence gating**: Any status of Present/Partial MUST include evidence IDs. If evidence is missing, status MUST be Absent or Needs-Review.
4. **Deterministic pipeline**:
   - Deterministic chunking (stable chunk IDs derived from doc hash + page + offsets).
   - Hybrid retrieval (FTS + vector) with deterministic tie-break rules.
   - LLM extraction uses temperature=0 and schema-only JSON output.
5. **Run reproducibility**: Every run stores a manifest containing:
   - input document hashes
   - requirements bundle versions
   - retrieval parameters
   - model identity and prompt hash
   - pipeline code version (git SHA)
6. **Caching by run hash**: Identical run inputs must reuse stored results and generate byte-identical outputs (excluding timestamps).
7. **No global implicit state** (e.g., environment variable RUN_ID): run_id must be explicit in function signatures and DB records.

## 3) Repo Workflow
- Work is delivered via small PRs (see PR conveyor files in `.github/codex/prompts/`).
- Each PR MUST:
  - Implement only its defined scope
  - Add/adjust tests
  - Pass `make lint` and `make test`
  - Update `PROJECT_STATE.md`
  - Add or update an ADR if changing an architectural decision

## 4) Code Standards
- Python 3.11+ for backend.
- Use type hints everywhere; prefer `pydantic` for IO and config.
- Prefer pure functions and explicit dependency injection.
- No large, unstructured prompts; use schema-based outputs.
- Do not commit generated artifacts (node_modules, .next, __pycache__, build outputs, PDFs, zips).

## 5) Testing Standards
- Unit tests for every non-trivial module.
- Determinism tests:
  - Chunk IDs stable across repeated ingestion
  - Retrieval ordering stable
  - Run hash cache returns identical outputs
- Snapshot tests allowed for HTML output but must normalize timestamps.

## 6) Runbook Commands (to be implemented in PR-001)
These commands MUST exist by end of PR-001:
- `make lint`
- `make test`
- `make dev` (optional)
- `make compose-up` / `make compose-down` (optional)

## 7) Security / Compliance
- Never exfiltrate document content to external services unless explicitly configured by user.
- Local LLM integration must be via an OpenAI-compatible base URL + key.
- Store documents immutably and hash them on ingestion.
- Tenant isolation required for production (later PRs).

## 8) PR Template Checklist Requirements
The PR template checklist is mandatory. If a PR changes architecture, it MUST add/update ADR(s).

## 9) What Codex Should Do First in Any PR
1. Read `AGENTS.md`, `PROJECT_STATE.md`, and relevant ADR(s).
2. Implement PR scope only.
3. Run required tests.
4. Update `PROJECT_STATE.md`.
5. Ensure CI readiness.
