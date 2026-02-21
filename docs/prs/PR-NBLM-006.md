# PR-NBLM-006 — NotebookLM MCP Provider Integration

## Checklist
- Added HTTP JSON-RPC NotebookLM MCP client with timeout/retry controls and typed errors.
- Added NotebookLM research provider implementing `ResearchProvider`.
- Added parser for markdown responses with trailing `CITATIONS:` block extraction.
- Added default `EU-CSRD-ESRS` notebook mapping to rollout notebook ID.
- Added tests for provider call order, parser extraction, and MCP retry behavior.

## Commands
- `make lint` ✅
- `make test` ✅
