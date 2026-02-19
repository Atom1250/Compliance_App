import os
import uuid
from contextlib import suppress

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError

from alembic import command
from alembic.config import Config


@pytest.mark.skipif(
    not os.getenv("COMPLIANCE_APP_POSTGRES_TEST_URL"),
    reason="COMPLIANCE_APP_POSTGRES_TEST_URL is not configured",
)
def test_postgres_migrations_upgrade_downgrade_upgrade_smoke() -> None:
    base_url = make_url(os.environ["COMPLIANCE_APP_POSTGRES_TEST_URL"])
    db_name = f"compliance_smoke_{uuid.uuid4().hex[:10]}"
    admin_url = base_url.set(database="postgres")
    target_url = base_url.set(database=db_name)

    admin_engine = create_engine(str(admin_url), isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    except OperationalError as exc:
        pytest.skip(f"postgres test user lacks database create privileges: {exc}")

    target_engine = None
    try:
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", str(target_url))
        command.upgrade(config, "head")
        command.downgrade(config, "base")
        command.upgrade(config, "head")

        target_engine = create_engine(str(target_url))
        with target_engine.connect() as conn:
            has_vector = conn.execute(
                text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            ).scalar()
            embedding_vector_type = conn.execute(
                text(
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_name = 'embedding' AND column_name = 'embedding_vector'"
                )
            ).scalar()
        assert bool(has_vector) is True
        assert embedding_vector_type == "USER-DEFINED"
    finally:
        if target_engine is not None:
            with suppress(Exception):
                target_engine.dispose()
        with admin_engine.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        admin_engine.dispose()
