from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.requirements.importer import import_bundle, load_bundle
from app.requirements.routing import resolve_bundle_selection
from apps.api.app.db.models import Company


def _prepare_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "bundle_routing.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    return Session(engine, expire_on_commit=False)


def _import_esrs_versions(session: Session) -> None:
    import_bundle(session, load_bundle(Path("requirements/esrs_mini/bundle.json")))
    import_bundle(session, load_bundle(Path("requirements/esrs_mini_legacy/bundle.json")))


def test_bundle_routing_selects_legacy_for_pre_2026(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        _import_esrs_versions(session)
        company = Company(name="Legacy Co", reporting_year_start=2022, reporting_year_end=2024)
        session.add(company)
        session.commit()

        resolved = resolve_bundle_selection(
            session,
            company_id=company.id,
            requested_bundle_id="esrs_mini",
            requested_bundle_version=None,
        )
        assert resolved.bundle_id == "esrs_mini"
        assert resolved.bundle_version == "2024.01"


def test_bundle_routing_selects_current_for_post_2026(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        _import_esrs_versions(session)
        company = Company(name="Current Co", reporting_year=2026)
        session.add(company)
        session.commit()

        resolved = resolve_bundle_selection(
            session,
            company_id=company.id,
            requested_bundle_id="esrs_mini",
            requested_bundle_version=None,
        )
        assert resolved.bundle_id == "esrs_mini"
        assert resolved.bundle_version == "2026.01"


def test_bundle_routing_preserves_explicit_override(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        _import_esrs_versions(session)
        company = Company(name="Override Co", reporting_year=2026)
        session.add(company)
        session.commit()

        resolved = resolve_bundle_selection(
            session,
            company_id=company.id,
            requested_bundle_id="esrs_mini",
            requested_bundle_version="2024.01",
        )
        assert resolved.bundle_id == "esrs_mini"
        assert resolved.bundle_version == "2024.01"

