# Postgres Cutover Validation Checklist

## Purpose
Operator checklist to validate Postgres + pgvector is functioning for full application workflow.

## Preconditions
1. Infra running:
   - `make compose-up`
   - `make db-wait`
2. Environment configured:
   - `COMPLIANCE_APP_DATABASE_URL=postgresql+psycopg://compliance:compliance@127.0.0.1:5432/compliance_app`
   - `COMPLIANCE_APP_ALLOW_SQLITE_TRANSITIONAL=false`
3. Migrations applied:
   - `alembic upgrade head`

## Validation Steps
1. Core quality gates:
   - `make lint`
   - `make test`
2. Postgres migration smoke:
   - `COMPLIANCE_APP_POSTGRES_TEST_URL=<postgres_url> python -m pytest tests/test_db_migrations_postgres.py`
3. Postgres E2E harness:
   - `python scripts/run_postgres_e2e.py --database-url <postgres_url>`
4. Dual-backend parity check (optional during transition):
   - `COMPLIANCE_APP_POSTGRES_TEST_URL=<postgres_url> python -m pytest tests/test_backend_parity.py`

## Expected Outcomes
- Run reaches `completed` in Postgres harness.
- Manifest endpoint returns bundle and retrieval policy metadata.
- Export readiness reports report/evidence pack ready.
- Report and evidence preview/download endpoints return success status.

## Rollback / Transitional Mode
- SQLite can still be used for explicit local troubleshooting only:
  - set `COMPLIANCE_APP_DATABASE_URL=sqlite:///...`
  - set `COMPLIANCE_APP_ALLOW_SQLITE_TRANSITIONAL=true`
