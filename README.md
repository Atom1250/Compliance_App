# Compliance_App

Initial project scaffold.

## Development

- Install: `python3 -m pip install -e .[dev]`
- Lint: `make lint`
- Test: `make test`
- UAT golden harness: `make uat`
- Install web deps: `make ui-setup`
- Launch full app locally (opens browser): `make dev`
- Default local URLs: UI `http://127.0.0.1:3001`, API `http://127.0.0.1:8001`
- Override ports if needed: `make dev WEB_PORT=3100 API_PORT=8100`

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

## Database

- Start Postgres: `docker compose up -d postgres`
- Run migrations: `alembic upgrade head`

## Object Storage

- Start MinIO: `docker compose up -d minio`
- Upload endpoint: `POST /documents/upload` (`company_id`, `title`, `file`)
- Retrieval endpoint: `GET /documents/{document_id}`
