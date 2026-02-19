from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import Company, Run


def _prepare_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "regulatory_defaults.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    return Session(engine, expire_on_commit=False)


def test_company_and_run_defaults_for_regulatory_mode_fields(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        company = Company(name="Defaults Co")
        session.add(company)
        session.commit()
        session.refresh(company)

        run = Run(company_id=company.id, status="queued")
        session.add(run)
        session.commit()
        session.refresh(run)

    assert company.regulatory_jurisdictions == "[]"
    assert company.regulatory_regimes == "[]"
    assert run.compiler_mode == "legacy"

