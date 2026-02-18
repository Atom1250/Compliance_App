from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.requirements.importer import import_bundle, load_bundle
from apps.api.app.db.models import ApplicabilityRule, DatapointDefinition, RequirementBundle


def _prepare_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "requirements.sqlite"
    db_url = f"sqlite:///{db_path}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    return Session(engine, expire_on_commit=False)


def test_sample_bundle_imports_and_stores_version(tmp_path: Path) -> None:
    bundle_path = Path("requirements/esrs_mini/bundle.json")
    bundle = load_bundle(bundle_path)

    with _prepare_session(tmp_path) as session:
        imported = import_bundle(session, bundle)

        stored_bundle = session.get(RequirementBundle, imported.id)
        datapoint_count = session.scalar(select(func.count(DatapointDefinition.id)))
        rule_count = session.scalar(select(func.count(ApplicabilityRule.id)))

    assert stored_bundle is not None
    assert stored_bundle.bundle_id == "esrs_mini"
    assert stored_bundle.version == "2026.01"
    assert datapoint_count == 2
    assert rule_count == 2


def test_import_is_idempotent(tmp_path: Path) -> None:
    bundle = load_bundle(Path("requirements/esrs_mini/bundle.json"))

    with _prepare_session(tmp_path) as session:
        first = import_bundle(session, bundle)
        second = import_bundle(session, bundle)

        bundle_count = session.scalar(select(func.count(RequirementBundle.id)))
        datapoint_count = session.scalar(select(func.count(DatapointDefinition.id)))
        rule_count = session.scalar(select(func.count(ApplicabilityRule.id)))

    assert first.id == second.id
    assert bundle_count == 1
    assert datapoint_count == 2
    assert rule_count == 2


def test_version_pin_allows_multiple_versions(tmp_path: Path) -> None:
    bundle = load_bundle(Path("requirements/esrs_mini/bundle.json"))
    bundle_v2 = bundle.model_copy(update={"version": "2026.02"})

    with _prepare_session(tmp_path) as session:
        imported_v1 = import_bundle(session, bundle)
        imported_v2 = import_bundle(session, bundle_v2)

        versions = session.scalars(
            select(RequirementBundle.version)
            .where(RequirementBundle.bundle_id == "esrs_mini")
            .order_by(RequirementBundle.version)
        ).all()

    assert imported_v1.id != imported_v2.id
    assert versions == ["2026.01", "2026.02"]
