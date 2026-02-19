from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.regulatory.cli import compile_preview, context_from_json, list_bundles, sync_bundles


def _prepare_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "regulatory_cli.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    return Session(engine, expire_on_commit=False)


def test_cli_helpers_list_sync_and_compile_preview(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        synced = sync_bundles(session, bundles_root=Path("app/regulatory/bundles"))
        assert synced

        bundles = list_bundles(session)
        assert bundles
        assert bundles[0][0] == "eu_csrd_sample"

        preview = compile_preview(
            session,
            bundle_id="eu_csrd_sample",
            version="2026.01",
            context={"company": {"reporting_year": 2026}},
        )
        assert preview["bundle_id"] == "eu_csrd_sample"
        assert preview["obligations"]


def test_context_from_json_requires_object() -> None:
    payload = context_from_json('{"company":{"reporting_year":2026}}')
    assert payload["company"]["reporting_year"] == 2026

    with pytest.raises(ValueError, match="context JSON must decode to an object"):
        context_from_json("[]")
