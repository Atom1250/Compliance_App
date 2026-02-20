# Regulatory Research Service

The Regulatory Research Service is a workflow utility layer for citation-backed regulatory research.

## Design guardrails
- Runtime scoring does not depend on this service.
- When disabled by flags, service returns deterministic stub responses and performs no external calls.
- Persistence is additive-only to `regulatory_requirement_research_notes`.

## Feature flags
- `COMPLIANCE_APP_FEATURE_REG_RESEARCH_ENABLED` (default: `false`)
- `COMPLIANCE_APP_FEATURE_NOTEBOOKLM_ENABLED` (default: `false`)
- `COMPLIANCE_APP_FEATURE_NOTEBOOKLM_STRICT_CITATIONS` (default: auto by environment; `true` in staging, `false` elsewhere)
- `COMPLIANCE_APP_FEATURE_NOTEBOOKLM_PERSIST_RESULTS` (default: `false`)
- `COMPLIANCE_APP_FEATURE_NOTEBOOKLM_FAIL_OPEN` (default: `false`)
- `COMPLIANCE_APP_NOTEBOOKLM_CACHE_TTL_DAYS` (default: `14`)
- `COMPLIANCE_APP_NOTEBOOKLM_CACHE_FAILURE_TTL_MINUTES` (default: `30`)

## NotebookLM rollout reference
- https://notebooklm.google.com/notebook/7bbf7d0b-db30-488e-8d2d-e7cbad3dbbe5
