from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.requirements.applicability import resolve_required_datapoint_ids
from app.requirements.importer import import_bundle, load_bundle
from apps.api.app.db.models import Company


def _prepare_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "legacy_resolution.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    return Session(engine, expire_on_commit=False)


def test_legacy_requirements_resolution_stability_registry_off(tmp_path: Path) -> None:
    """Locks baseline resolver behavior in direct bundle mode (registry off/default)."""
    bundle = load_bundle(Path("requirements/esrs_mini/bundle.json"))

    with _prepare_session(tmp_path) as session:
        import_bundle(session, bundle)
        company = Company(
            name="Legacy Stability Co",
            listed_status=True,
            reporting_year=2026,
        )
        session.add(company)
        session.commit()

        resolved = resolve_required_datapoint_ids(
            session,
            company_id=company.id,
            bundle_id="esrs_mini",
            bundle_version="2026.01",
        )

    assert "ESRS-E1-1" in resolved
    assert "ESRS-E1-6" in resolved
