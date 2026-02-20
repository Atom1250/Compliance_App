# NotebookLM MCP Local Setup

## Purpose
Run NotebookLM MCP as a local sidecar for internal regulatory research workflows.

## 1) Configure image
Set the MCP image before startup:

```bash
export NOTEBOOKLM_MCP_IMAGE=ghcr.io/your-org/notebooklm-mcp:latest
```

## 2) Start sidecar

```bash
docker compose -f docker/compose.notebooklm.yml up -d
docker compose -f docker/compose.notebooklm.yml ps
```

## 3) One-time service-user login
1. Open the MCP sidecar container logs:
   ```bash
   docker compose -f docker/compose.notebooklm.yml logs -f notebooklm-mcp
   ```
2. Complete login flow using the dedicated service account (never personal account).
3. Confirm session/profile is persisted in Docker volume `notebooklm_profile`.

## 4) Wire API flags
Set in `.env`:

```bash
COMPLIANCE_APP_FEATURE_REG_RESEARCH_ENABLED=true
COMPLIANCE_APP_FEATURE_NOTEBOOKLM_ENABLED=true
COMPLIANCE_APP_NOTEBOOKLM_MCP_BASE_URL=http://127.0.0.1:3000
COMPLIANCE_APP_NOTEBOOKLM_NOTEBOOK_MAP_JSON={"EU-CSRD-ESRS":"7bbf7d0b-db30-488e-8d2d-e7cbad3dbbe5"}
```

Restart API after changes.

## 5) Session rotation
1. Stop sidecar.
2. Remove `notebooklm_profile` volume:
   ```bash
   docker volume rm compliance_app_notebooklm_profile
   ```
3. Start sidecar and repeat login.

## Safety
- If sidecar is down, scoring remains unaffected.
- Disable workflows immediately with:
  - `COMPLIANCE_APP_FEATURE_NOTEBOOKLM_ENABLED=false`
  - or `COMPLIANCE_APP_FEATURE_REG_RESEARCH_ENABLED=false`
