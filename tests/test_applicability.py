from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.requirements.applicability import resolve_required_datapoint_ids
from app.requirements.importer import import_bundle, load_bundle
from apps.api.app.db.models import Company


def _prepare_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "applicability.sqlite"
    db_url = f"sqlite:///{db_path}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    return Session(engine, expire_on_commit=False)


def test_applicability_returns_expected_datapoints_for_fixture(tmp_path: Path) -> None:
    bundle = load_bundle(Path("requirements/esrs_mini/bundle.json"))

    with _prepare_session(tmp_path) as session:
        import_bundle(session, bundle)

        company = Company(
            name="Fixture Co",
            employees=320,
            turnover=25_000_000.0,
            listed_status=True,
            reporting_year=2026,
        )
        session.add(company)
        session.commit()

        required = resolve_required_datapoint_ids(
            session,
            company_id=company.id,
            bundle_id="esrs_mini",
            bundle_version="2026.01",
        )

    assert required == ["ESRS-E1-1", "ESRS-E1-6"]


def test_applicability_rule_evaluation_filters_out_non_applicable(tmp_path: Path) -> None:
    bundle = load_bundle(Path("requirements/esrs_mini/bundle.json"))

    with _prepare_session(tmp_path) as session:
        import_bundle(session, bundle)

        company = Company(
            name="Pre-threshold Co",
            employees=80,
            turnover=1_000_000.0,
            listed_status=False,
            reporting_year=2024,
        )
        session.add(company)
        session.commit()

        required = resolve_required_datapoint_ids(
            session,
            company_id=company.id,
            bundle_id="esrs_mini",
            bundle_version="2026.01",
        )

    assert required == []
