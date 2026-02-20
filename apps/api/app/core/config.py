"""Environment-driven API configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "Compliance App API"
    app_version: str = "0.1.0"
    database_url: str = "postgresql+psycopg://compliance:compliance@localhost:5432/compliance_app"
    runtime_environment: str = "development"
    allow_sqlite_transitional: bool = False
    object_storage_root: Path = Path(".data/object_store")
    object_storage_uri_prefix: str = "file://"
    evidence_pack_output_root: Path = Path("outputs/evidence_packs")
    pdf_export_enabled: bool = False
    llm_base_url: str = "http://127.0.0.1:1234"
    llm_api_key: str = "lm-studio"
    llm_model: str = "ministral-3-8b-instruct-2512-mlx"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    startup_validate_providers: str = ""
    git_sha: str = "unknown"
    security_enabled: bool = True
    auth_api_keys: str = "dev-key"
    auth_tenant_keys: str = "default:dev-key"
    request_rate_limit_enabled: bool = True
    request_rate_limit_window_seconds: int = 60
    request_rate_limit_max_requests: int = 30
    cors_allowed_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001,"
        "http://localhost:3002,http://127.0.0.1:3002,"
        "http://host.docker.internal:3000,http://host.docker.internal:3001,"
        "http://host.docker.internal:3002"
    )
    cors_allowed_origin_regex: str = (
        r"https?://(localhost|127\.0\.0\.1|host\.docker\.internal)(:\d+)?$"
    )
    tavily_enabled: bool = False
    tavily_api_key: str = ""
    tavily_base_url: str = "https://api.tavily.com/search"
    tavily_timeout_seconds: float = 20.0
    tavily_max_results: int = 8
    tavily_download_timeout_seconds: float = 30.0
    tavily_max_document_bytes: int = 50000000
    tavily_discovery_budget_seconds: float = 60.0
    integrity_warning_failure_threshold: float = 0.4
    feature_registry_compiler: bool = False
    feature_registry_report_matrix: bool = False
    regulatory_registry_sync_enabled: bool = False
    regulatory_registry_bundles_root: Path = Path("app/regulatory/bundles")

    model_config = SettingsConfigDict(
        env_prefix="COMPLIANCE_APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
