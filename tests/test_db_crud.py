from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import Company, Run


def _migrated_engine(tmp_path: Path):
    db_path = tmp_path / "crud.sqlite"
    db_url = f"sqlite:///{db_path}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")

    return create_engine(db_url)


def test_company_and_run_crud(tmp_path: Path) -> None:
    engine = _migrated_engine(tmp_path)

    with Session(engine) as session:
        company = Company(name="Example Corp")
        session.add(company)
        session.flush()

        run = Run(company_id=company.id, status="queued")
        session.add(run)
        session.commit()

    with Session(engine) as session:
        loaded_company = session.scalar(select(Company).where(Company.name == "Example Corp"))
        loaded_run = session.scalar(select(Run).where(Run.status == "queued"))

    assert loaded_company is not None
    assert loaded_run is not None
    assert loaded_run.company_id == loaded_company.id
