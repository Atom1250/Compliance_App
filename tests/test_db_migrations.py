from pathlib import Path

from sqlalchemy import create_engine, inspect

from alembic import command
from alembic.config import Config

REQUIRED_TABLES = {
    "applicability_rule",
    "alembic_version",
    "chunk",
    "company",
    "datapoint_def",
    "datapoint_assessment",
    "document",
    "document_discovery_candidate",
    "document_file",
    "document_page",
    "embedding",
    "requirement_bundle",
    "regulatory_bundle",
    "run",
    "run_cache_entry",
    "run_manifest",
    "run_registry_artifact",
    "run_materiality",
    "run_event",
}


def _alembic_config_for(url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    return config


def test_migrations_upgrade_head_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "migrations.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = _alembic_config_for(db_url)

    command.upgrade(config, "head")
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    inspector = inspect(engine)
    assert REQUIRED_TABLES.issubset(set(inspector.get_table_names()))


def test_regulatory_bundle_migration_upgrade_and_downgrade(tmp_path: Path) -> None:
    db_path = tmp_path / "regulatory_bundle_migration.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = _alembic_config_for(db_url)

    command.upgrade(config, "head")
    engine = create_engine(db_url)
    inspector = inspect(engine)
    assert "regulatory_bundle" in set(inspector.get_table_names())

    command.downgrade(config, "0012_company_reporting_year_range")
    inspector = inspect(engine)
    assert "regulatory_bundle" not in set(inspector.get_table_names())

    command.upgrade(config, "head")
    inspector = inspect(engine)
    assert "regulatory_bundle" in set(inspector.get_table_names())
