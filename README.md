# Compliance_App

Initial project scaffold.

## Development

- Install: `python3 -m pip install -e .[dev]`
- Lint: `make lint`
- Test: `make test`

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
