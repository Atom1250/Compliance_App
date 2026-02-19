# Local Infra Runbook: Postgres + pgvector + MinIO

## Services
- Postgres (pgvector-enabled): `pgvector/pgvector:pg16`
- MinIO (S3-compatible object storage): `minio/minio`

## Commands
1. Start services:
   - `make compose-up`
2. Wait for Postgres readiness:
   - `make db-wait`
3. Stop services:
   - `make compose-down`

## Notes
- Postgres init scripts are mounted from `docker/postgres/init`.
- pgvector extension bootstrap script:
  - `docker/postgres/init/001-enable-pgvector.sql`
- Runtime policy:
  - Postgres is the system-of-record backend.
  - SQLite is transitional/test-only and requires explicit opt-in via
    `COMPLIANCE_APP_ALLOW_SQLITE_TRANSITIONAL=true`.
