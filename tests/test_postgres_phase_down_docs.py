from pathlib import Path


def test_readme_marks_sqlite_as_transitional_only() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "SQLite is transitional/test-only" in readme
    assert "COMPLIANCE_APP_ALLOW_SQLITE_TRANSITIONAL=true" in readme
    assert "Postgres is the runtime system-of-record." in readme


def test_cutover_runbook_exists_with_validation_steps() -> None:
    runbook_path = Path("docs/runbooks/postgres_cutover_validation.md")
    assert runbook_path.exists()
    runbook = runbook_path.read_text(encoding="utf-8")
    assert "Postgres E2E harness" in runbook
    assert "make lint" in runbook
    assert "make test" in runbook
    assert "COMPLIANCE_APP_ALLOW_SQLITE_TRANSITIONAL=false" in runbook
