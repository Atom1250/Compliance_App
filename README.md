# Compliance_App

Initial project scaffold.

## Development

- Python setup (creates `.venv` + installs deps): `make setup`
- Create local env file: `cp .example.env .env` (then fill keys)
- Lint: `make lint`
- Test: `make test`
- UAT golden harness: `make uat`
- Install web deps: `make ui-setup`
- Launch full app locally (opens browser): `make dev`
- Default local URLs: UI `http://127.0.0.1:3001`, API `http://127.0.0.1:8001`
- Override ports if needed: `make dev WEB_PORT=3100 API_PORT=8100`
- `make dev` uses local SQLite by default (`sqlite:///outputs/dev/compliance_app.sqlite`) and runs migrations automatically.
- `make dev`, `make dev-api`, and `make dev-web` auto-load `.env` when present.

## UAT Harness

Run deterministic end-to-end UAT (company -> upload -> execute -> report -> evidence pack):

- Command: `make uat`
- Golden artifact: `tests/golden/uat_harness_snapshot.json`
- Update golden (intentional contract change only):
  - `python3 scripts/run_uat_harness.py --update-golden`

## API

- Run API: `uvicorn apps.api.main:app --reload`
- Health: `GET /healthz`
- Version: `GET /version`

## Auto-Discover ESG Documents (Tavily)

The Upload page now supports:
- Manual upload with explicit `title`
- `Auto-Find ESG Documents` (search + download + ingest)

Enable Tavily discovery:
- `export COMPLIANCE_APP_TAVILY_ENABLED=true`
- `export COMPLIANCE_APP_TAVILY_API_KEY=your_tavily_key`

Optional tuning:
- `COMPLIANCE_APP_TAVILY_MAX_RESULTS` (default `8`)
- `COMPLIANCE_APP_TAVILY_TIMEOUT_SECONDS` (default `20`)
- `COMPLIANCE_APP_TAVILY_DOWNLOAD_TIMEOUT_SECONDS` (default `30`)
- `COMPLIANCE_APP_TAVILY_MAX_DOCUMENT_BYTES` (default `10000000`)

## Database

- Start Postgres: `docker compose up -d postgres`
- Run migrations: `alembic upgrade head`

## Object Storage

- Start MinIO: `docker compose up -d minio`
- Upload endpoint: `POST /documents/upload` (`company_id`, `title`, `file`)
- Retrieval endpoint: `GET /documents/{document_id}`
