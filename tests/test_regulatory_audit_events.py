from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.services import regulatory_registry as registry_module


def _prepare_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "regulatory_audit.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    return Session(engine, expire_on_commit=False)


def test_regulatory_sync_and_compile_emit_audit_events(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def _fake_log_structured_event(event_type: str, **fields):
        del fields
        calls.append(event_type)
        return event_type

    monkeypatch.setattr(registry_module, "log_structured_event", _fake_log_structured_event)

    with _prepare_session(tmp_path) as session:
        registry_module.sync_from_filesystem(session, bundles_root=Path("app/regulatory/bundles"))
        registry_module.compile_from_db(
            session,
            bundle_id="eu_csrd_sample",
            version="2026.01",
            context={"company": {"reporting_year": 2026}},
        )

    assert "regulatory.sync.started" in calls
    assert "regulatory.sync.completed" in calls
    assert "regulatory.compile.started" in calls
    assert "regulatory.compile.completed" in calls
