import json
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import RegulatoryBundle
from apps.api.app.services.regulatory_registry import compile_from_db, sync_from_filesystem


def _prepare_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "regulatory_end_to_end.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    return Session(engine, expire_on_commit=False)


def test_sync_and_compile_are_deterministic_for_seeded_bundles(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        first_sync = sync_from_filesystem(session, bundles_root=Path("app/regulatory/bundles"))
        second_sync = sync_from_filesystem(session, bundles_root=Path("app/regulatory/bundles"))
        assert first_sync == second_sync

        rows = session.scalars(
            select(RegulatoryBundle).order_by(RegulatoryBundle.bundle_id, RegulatoryBundle.version)
        ).all()
        assert [row.bundle_id for row in rows] == [
            "csrd_esrs_core",
            "eu_csrd_sample",
            "eu_green_bond_sample",
            "no_transparency_sample",
            "uk_sdr_sample",
        ]

        context = {"company": {"reporting_year": 2026, "listed_status": True}}
        compiled_once = [
            compile_from_db(
                session,
                bundle_id=row.bundle_id,
                version=row.version,
                context=context,
            ).model_dump(mode="json")
            for row in rows
        ]
        compiled_twice = [
            compile_from_db(
                session,
                bundle_id=row.bundle_id,
                version=row.version,
                context=context,
            ).model_dump(mode="json")
            for row in rows
        ]
        assert json.dumps(compiled_once, sort_keys=True, separators=(",", ":")) == json.dumps(
            compiled_twice, sort_keys=True, separators=(",", ":")
        )
        assert all(plan["obligations"] for plan in compiled_once)
