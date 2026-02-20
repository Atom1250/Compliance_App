# NotebookLM Breakage Response

## Statement
NotebookLM is workflow-only and is not used in runtime compliance scoring.

## Kill switch (<= 3 steps)
1. Set `COMPLIANCE_APP_FEATURE_NOTEBOOKLM_ENABLED=false`.
2. If needed, set `COMPLIANCE_APP_FEATURE_REG_RESEARCH_ENABLED=false`.
3. Restart API process.

## Fallback behavior
- Internal research routes return deterministic disabled/stub behavior.
- Scoring pipeline continues unchanged.

## Investigation checklist
- Verify sidecar health and reachability.
- Verify service-account session validity.
- Check MCP error logs and response schema changes.
- Validate citations parser output contract.
