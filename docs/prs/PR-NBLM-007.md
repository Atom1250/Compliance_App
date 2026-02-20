# PR-NBLM-007 — Infra Sidecar (NotebookLM MCP)

## Checklist
- Added sidecar compose file: `docker/compose.notebooklm.yml`.
- Added persistent Docker volumes for NotebookLM profile/config.
- Added local setup runbook with service-account login + session rotation.
- Added `.gitignore` protection for local NotebookLM artifacts.

## Commands
- `make lint` ✅
- `make test` ✅
