# NotebookLM Manual Integration Tests (Non-CI)

CI does not require NotebookLM MCP. Use this runbook for staging/manual verification.

## Preconditions
- NotebookLM MCP sidecar running and healthy.
- Service account logged in.
- Feature flags enabled for regulatory research and NotebookLM.

## Steps
1. Run API.
2. Call internal workflow endpoint:

```bash
curl -sS \
  -H "X-API-Key: dev-key" \
  -H "X-Tenant-ID: default" \
  -H "Content-Type: application/json" \
  -X POST "http://127.0.0.1:8001/internal/regulatory-research/query" \
  -d '{
    "question":"Map ESRS E1-1 transition plan obligations",
    "corpus_key":"EU-CSRD-ESRS",
    "mode":"mapping"
  }' | jq
```

3. Verify response includes:
- `provider: "notebooklm"`
- `answer_markdown` non-empty
- `citations` present in strict mode

## Expected failure behavior
- If sidecar unavailable, endpoint returns controlled error and scoring APIs remain unaffected.
- If feature flags disabled, endpoint returns `404` (`regulatory research feature disabled`).
