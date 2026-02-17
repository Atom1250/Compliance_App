"""Database engine and session management."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from apps.api.app.core.config import get_settings


def get_engine() -> Engine:
    """Create SQLAlchemy engine from explicit settings."""
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True)


def get_session_factory() -> sessionmaker[Session]:
    """Return session factory bound to configured engine."""
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


def get_db_session() -> Generator[Session, None, None]:
    """Yield database session for request-scoped usage."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
