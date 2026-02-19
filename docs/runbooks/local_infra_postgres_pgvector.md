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
- Current make targets provision infra only; application runtime cutover to Postgres as default is
  handled in follow-up PRs.
