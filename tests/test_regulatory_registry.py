from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.regulatory.schema import RegulatoryBundle
from apps.api.app.db.models import RegulatoryBundle as RegulatoryBundleRecord
from apps.api.app.services.regulatory_registry import get_bundle, upsert_bundle


def _prepare_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "regulatory_registry.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    return Session(engine, expire_on_commit=False)


def _bundle_payload(version: str = "2026.01") -> dict[str, object]:
    return {
        "bundle_id": "eu_csrd_sample",
        "version": version,
        "jurisdiction": "EU",
        "regime": "CSRD_ESRS",
        "obligations": [],
    }


def test_upsert_bundle_is_idempotent(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        bundle = RegulatoryBundle.model_validate(_bundle_payload())
        first = upsert_bundle(session, bundle=bundle)
        second = upsert_bundle(session, bundle=bundle)

        count = int(session.scalar(select(func.count()).select_from(RegulatoryBundleRecord)) or 0)
        assert first.id == second.id
        assert count == 1


def test_get_bundle_returns_stored_row(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        bundle = RegulatoryBundle.model_validate(_bundle_payload())
        stored = upsert_bundle(session, bundle=bundle)
        loaded = get_bundle(session, bundle_id="eu_csrd_sample", version="2026.01")

        assert loaded is not None
        assert loaded.id == stored.id
        assert loaded.checksum == stored.checksum


def test_upsert_bundle_updates_changed_checksum(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        base_payload = _bundle_payload(version="2026.01")
        updated_payload = _bundle_payload(version="2026.01")
        updated_payload["obligations"] = [
            {
                "obligation_id": "OBL-1",
                "title": "Updated",
                "standard_reference": "ESRS E1-1",
                "elements": [],
            }
        ]
        base = RegulatoryBundle.model_validate(base_payload)
        updated = RegulatoryBundle.model_validate(updated_payload)

        first = upsert_bundle(session, bundle=base)
        first_checksum = first.checksum
        second = upsert_bundle(session, bundle=updated)

        count = int(session.scalar(select(func.count()).select_from(RegulatoryBundleRecord)) or 0)
        assert count == 1
        assert second.id == first.id
        assert second.checksum != first_checksum
