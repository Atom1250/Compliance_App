# UAT Execution Runbook

## Purpose
Run deterministic end-to-end UAT scenarios and validate contract outputs against the versioned golden snapshot.

## Prerequisites
- Python 3.11 environment with project dependencies installed.
- Local checkout of this repository.
- No external API access is required for default UAT scenarios.

## Commands
1. Run harness and compare to golden snapshot:
   - `python scripts/run_uat_harness.py`
2. If expected changes were made intentionally, update golden:
   - `python scripts/run_uat_harness.py --update-golden`
3. Run only pytest harness assertions:
   - `python -m pytest tests/test_uat_harness.py`

## Scenario Pack
- Fixture file: `tests/fixtures/uat/scenarios.json`
- Includes:
  - `local_deterministic_success` (local deterministic provider path)
  - `openai_missing_key_failure` (cloud provider failure contract path)

## Expected Contracts
- Successful scenario:
  - run reaches `completed`
  - `/runs/{id}/report` returns `200`
  - `/runs/{id}/evidence-pack-preview` returns `200`
- Failed scenario:
  - run reaches `failed`
  - `/runs/{id}/report` returns `409`
  - `/runs/{id}/evidence-pack-preview` returns `409`

## Troubleshooting
- If harness fails on golden mismatch:
  - inspect output diff from `scripts/run_uat_harness.py`
  - confirm change is intentional and deterministic
  - update golden snapshot only after review
- If harness fails on migrations:
  - run `python -m pytest tests/test_db_migrations.py`
