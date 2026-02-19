from pathlib import Path


def test_example_env_defaults_database_url_to_postgres() -> None:
    text = Path(".example.env").read_text()
    assert (
        "COMPLIANCE_APP_DATABASE_URL="
        "postgresql+psycopg://compliance:compliance@127.0.0.1:5432/compliance_app"
    ) in text


def test_makefile_dev_database_url_default_is_postgres() -> None:
    text = Path("Makefile").read_text()
    assert (
        "DEV_DATABASE_URL ?= "
        "postgresql+psycopg://compliance:compliance@127.0.0.1:5432/compliance_app"
    ) in text
