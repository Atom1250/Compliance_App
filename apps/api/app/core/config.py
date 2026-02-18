"""Environment-driven API configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "Compliance App API"
    app_version: str = "0.1.0"
    database_url: str = "postgresql+psycopg://compliance:compliance@localhost:5432/compliance_app"
    object_storage_root: Path = Path(".data/object_store")
    object_storage_uri_prefix: str = "file://"
    pdf_export_enabled: bool = False

    model_config = SettingsConfigDict(env_prefix="COMPLIANCE_APP_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
