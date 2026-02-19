from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.services.regulatory_registry import compile_from_db, sync_from_filesystem


def _prepare_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "regulatory_compile.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    return Session(engine, expire_on_commit=False)


def test_compile_from_db_after_sync(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        synced = sync_from_filesystem(session, bundles_root=Path("app/regulatory/bundles"))
        assert synced

        plan = compile_from_db(
            session,
            bundle_id="eu_csrd_sample",
            version="2026.01",
            context={"company": {"reporting_year": 2026}},
        )

    assert plan.bundle_id == "eu_csrd_sample"
    assert plan.version == "2026.01"
    assert len(plan.obligations) == 1
    assert plan.obligations[0].obligation_id == "ESRS-E1-1"


def test_compile_from_db_raises_when_bundle_missing(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        with pytest.raises(ValueError, match="Bundle not found: missing@1"):
            compile_from_db(
                session,
                bundle_id="missing",
                version="1",
                context={"company": {"reporting_year": 2026}},
            )
