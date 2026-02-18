# Analysis Passes (Consolidated)

This file documents the current end-to-end analysis passes executed by the Compliance App pipeline.

## Pass Sequence

1. `P00 - Company profile capture`
- Endpoint: `POST /companies`
- Captures profile fields used for applicability (`employees`, `turnover`, `listed_status`, `reporting_year`, `reporting_year_start`, `reporting_year_end`).
- Code: `apps/api/app/api/routers/companies.py`

2. `P01 - Document ingestion and dedupe`
- Endpoint: `POST /documents/upload` (or auto-discovery path).
- Computes `sha256`, deduplicates per tenant, stores immutable bytes.
- Code: `apps/api/app/services/document_ingestion.py`

3. `P02 - Deterministic page extraction`
- Extracts page text (PDF path first), persists `document_page`.
- Code: `apps/api/app/services/document_extraction.py`

4. `P03 - Deterministic chunking`
- Builds stable chunk IDs using `sha256(doc_hash:page:start:end)`.
- Persists chunks ordered by page and offsets.
- Code: `apps/api/app/services/chunking.py`

5. `P04 - Run creation`
- Endpoint: `POST /runs`
- Creates run row (`queued`) and emits `run.created`.
- Code: `apps/api/app/api/routers/materiality.py`

6. `P05 - Run execution bootstrap`
- Endpoint: `POST /runs/{run_id}/execute`
- Enqueues worker, sets `running`, emits `run.execution.started`.
- Selects provider: `deterministic_fallback`, `local_lm_studio`, `openai_cloud`.
- Code: `apps/api/app/services/run_execution_worker.py`, `apps/api/app/services/llm_provider.py`

7. `P06 - Requirements resolution (applicability pass)`
- Resolves required datapoints from selected bundle/version.
- Applies safe expression evaluation against company profile (including year range fields).
- Code: `app/requirements/applicability.py`

8. `P07 - Retrieval pass (per datapoint)`
- Hybrid lexical/vector retrieval with deterministic tie-break (`chunk_id`).
- Explicit retrieval policy and stable sorting.
- Code: `apps/api/app/services/retrieval.py`

9. `P08 - LLM extraction pass (per datapoint)`
- Builds strict prompt from datapoint + retrieved chunk text.
- Executes schema-only JSON extraction with `temperature=0.0`.
- Enforces evidence gating (`Present/Partial` must include evidence IDs).
- Code: `apps/api/app/services/llm_extraction.py`

10. `P09 - Verification pass (per datapoint)`
- Verifies cited evidence consistency (chunk existence, values/years/units).
- Deterministically downgrades status when validation fails.
- Code: `apps/api/app/services/verification.py`

11. `P10 - Assessment persistence`
- Persists `datapoint_assessment` rows with rationale, evidence IDs, prompt hash, retrieval params.
- Emits `assessment.pipeline.completed`.
- Code: `apps/api/app/services/assessment_pipeline.py`

12. `P11 - Run-hash cache pass`
- Computes canonical run hash from inputs (documents/profile/materiality/bundle/retrieval/prompt).
- Reuses cached output on identical inputs.
- Code: `apps/api/app/services/run_cache.py`

13. `P12 - Manifest and completion`
- Persists `run_manifest` with document hashes, bundle version, retrieval params, model, prompt hash, git SHA.
- Marks run `completed` and emits `run.execution.completed`.
- Code: `apps/api/app/services/run_manifest.py`, `apps/api/app/services/run_execution_worker.py`

14. `P13 - Report and evidence-pack generation`
- Report HTML served at `GET /runs/{run_id}/report` (completed runs only).
- Evidence pack ZIP served at `GET /runs/{run_id}/evidence-pack`.
- Code: `apps/api/app/api/routers/materiality.py`, `apps/api/app/services/evidence_pack.py`, `apps/api/app/services/reporting.py`

## Per-Datapoint Sub-Pass Loop

For each required datapoint (sorted key order), the system runs:

1. Query build from datapoint title/reference.
2. Retrieval (`top_k`, deterministic ordering).
3. LLM extraction (schema JSON only).
4. Verification/downgrade checks.
5. Assessment row persistence.

Code: `apps/api/app/services/assessment_pipeline.py`

## Provider Behavior in LLM Pass

1. `deterministic_fallback`
- No external LLM call.
- Emits deterministic `Absent` result with fixed rationale.
- Code: `apps/api/app/services/run_execution_worker.py`

2. `local_lm_studio`
- OpenAI-compatible transport to local base URL.
- Code: `apps/api/app/services/llm_provider.py`

3. `openai_cloud`
- OpenAI-compatible transport to cloud endpoint.
- Requires API key.
- Code: `apps/api/app/services/llm_provider.py`

## Primary Run Events (Audit Trail)

1. `run.created`
2. `run.execution.queued`
3. `run.execution.started`
4. `assessment.pipeline.started`
5. `assessment.pipeline.completed`
6. `run.execution.completed` or `run.execution.failed`
7. `run.report.requested`
8. `run.status.requested`

Event helpers: `apps/api/app/services/audit.py`
