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
- `make dev` uses local Postgres by default (`postgresql+psycopg://compliance:compliance@127.0.0.1:5432/compliance_app`) and runs migrations automatically.
- SQLite is transitional/test-only. To run transitional SQLite locally, explicitly set:
  - `COMPLIANCE_APP_DATABASE_URL=sqlite:///outputs/dev/compliance_app.sqlite make dev`
  - `COMPLIANCE_APP_ALLOW_SQLITE_TRANSITIONAL=true`
- `make dev`, `make dev-api`, and `make dev-web` auto-load `.env` when present.
- `make dev` and `make dev-api` also auto-import requirements bundles (`esrs_mini`, `green_finance_mini`) so run execution can start without manual DB seeding.

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

## LLM Provider Comparison

Run configuration now supports:
- `deterministic_fallback`
- `local_lm_studio`
- `openai_cloud`
- `esrs_mini@2026.01` (current baseline)
- `esrs_mini@2024.01` (legacy/pre-2026 historical testing)

Company setup supports reporting year ranges (`start/end`), and applicability uses
`reporting_year_end` as the effective year for rule evaluation.

Cloud provider env vars:
- `COMPLIANCE_APP_OPENAI_BASE_URL` (default `https://api.openai.com/v1`)
- `COMPLIANCE_APP_OPENAI_API_KEY`
- `COMPLIANCE_APP_OPENAI_MODEL` (default `gpt-4o-mini`)

## Run Diagnostics

Use the run diagnostics script to identify where a run fails or goes empty:

- `python scripts/diagnose_run.py --database-url sqlite:///outputs/dev/compliance_app.sqlite --run-id <RUN_ID>`

If older runs/documents are missing chunks, backfill them without resetting the DB:

- `python scripts/backfill_chunks.py --database-url sqlite:///outputs/dev/compliance_app.sqlite`

## Database

- Start Postgres: `make compose-up` (or `docker compose up -d postgres`)
- Wait for readiness: `make db-wait`
- Run migrations: `alembic upgrade head`
- Postgres is the runtime system-of-record. SQLite is only supported for explicit transitional/test workflows.

## Object Storage

- Start MinIO: `docker compose up -d minio`
- Upload endpoint: `POST /documents/upload` (`company_id`, `title`, `file`)
- Retrieval endpoint: `GET /documents/{document_id}`
