# ADR-0003: NotebookLM MCP as Regulatory Research Service (Workflow Only)

Date: 2026-02-20
Status: Accepted

## Context
The application already uses versioned regulatory bundles, deterministic importers, and DB-backed run manifests as the system-of-record for compliance scoring.

We want faster policy research and requirement mapping support for internal workflows, but we must not create runtime scoring dependencies on third-party notebook tooling.

## Decision
Adopt NotebookLM via MCP as an internal **Regulatory Research Service** to support workflow activities (tagging, mapping, Q&A, draft PRD support) only.

Initial rollout notebook:
- https://notebooklm.google.com/notebook/7bbf7d0b-db30-488e-8d2d-e7cbad3dbbe5

### Hard constraints
- **No scoring path calls NotebookLM.**
- NotebookLM results are additive research notes only; canonical requirement/scoring records are not mutated directly by NotebookLM responses.
- **NotebookLM integration behind feature flags + kill switch.**
- If feature flags are OFF, the service returns deterministic disabled responses and performs no external calls.

## Non-goals
- Runtime compliance scoring, datapoint status computation, or evidence gating decisions using NotebookLM.
- Replacing curated requirements bundles or deterministic compiler logic.

## Risks
- MCP/provider behavior may change without notice.
- Auth/session/profile state can break due to browser/profile drift.
- External response quality variability can reduce citation quality.

## Governance
- Authentication via dedicated service account only.
- Chrome profile/session storage for NotebookLM integration must be isolated from personal accounts and stored in controlled service paths.
- Data classification: NotebookLM research inputs limited to public regulatory content for this phase.
- No tenant-sensitive private documents routed to NotebookLM in this rollout.

## Breakage Response Plan
1. Disable `FEATURE_NOTEBOOKLM_ENABLED` or `FEATURE_REG_RESEARCH_ENABLED` immediately.
2. Keep workflow functional via stub response/fallback path (no external call).
3. Preserve scoring behavior because scoring path has no NotebookLM dependency.
4. Record incident + root cause, then re-enable only after regression checks pass.

## Consequences
Pros:
- Faster regulatory mapping workflows.
- Reusable citation-backed research notes and caching.
- Clear isolation from runtime scoring risk.

Cons:
- Additional operational dependency for workflow tooling.
- Requires active monitoring of feature flags and provider health.
