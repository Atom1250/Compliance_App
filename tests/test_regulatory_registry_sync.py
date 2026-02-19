import json
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import RegulatoryBundle as RegulatoryBundleRecord
from apps.api.app.services.regulatory_registry import sync_from_filesystem


def _prepare_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "regulatory_registry_sync.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    return Session(engine, expire_on_commit=False)


def _write_bundle(path: Path, *, bundle_id: str, version: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "bundle_id": bundle_id,
        "version": version,
        "jurisdiction": "EU",
        "regime": "CSRD_ESRS",
        "obligations": [],
    }
    path.write_text(json.dumps(payload))


def test_sync_from_filesystem_is_idempotent(tmp_path: Path) -> None:
    bundles_root = tmp_path / "bundles"
    _write_bundle(bundles_root / "b.json", bundle_id="bundle-b", version="2026.01")
    _write_bundle(bundles_root / "a.json", bundle_id="bundle-a", version="2026.01")

    with _prepare_session(tmp_path) as session:
        first = sync_from_filesystem(session, bundles_root=bundles_root)
        second = sync_from_filesystem(session, bundles_root=bundles_root)
        count = int(session.scalar(select(func.count()).select_from(RegulatoryBundleRecord)) or 0)

    assert first == second
    assert count == 2


def test_sync_from_filesystem_returns_deterministic_order(tmp_path: Path) -> None:
    bundles_root = tmp_path / "bundles"
    _write_bundle(
        bundles_root / "nested" / "z.json",
        bundle_id="bundle-z",
        version="2026.01",
    )
    _write_bundle(
        bundles_root / "nested" / "m.json",
        bundle_id="bundle-m",
        version="2026.01",
    )

    with _prepare_session(tmp_path) as session:
        synced = sync_from_filesystem(session, bundles_root=bundles_root)

    assert [item[0] for item in synced] == ["bundle-m", "bundle-z"]

