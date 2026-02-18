from apps.api.app.core.config import Settings
from apps.api.app.services.llm_provider import build_extraction_client_from_settings


def test_lm_studio_provider_uses_configured_model_and_base_url() -> None:
    settings = Settings(
        llm_base_url="http://127.0.0.1:1234",
        llm_api_key="lm-studio",
        llm_model="ministral-3-8b-instruct-2512-mlx",
    )

    client = build_extraction_client_from_settings(settings)
    assert client.model_name == "ministral-3-8b-instruct-2512-mlx"


def test_openai_cloud_provider_uses_cloud_model() -> None:
    settings = Settings(
        openai_base_url="https://api.openai.com/v1",
        openai_api_key="test-key",
        openai_model="gpt-4o-mini",
    )

    client = build_extraction_client_from_settings(settings, provider="openai_cloud")
    assert client.model_name == "gpt-4o-mini"


def test_openai_cloud_provider_requires_api_key() -> None:
    settings = Settings(openai_api_key="")
    try:
        build_extraction_client_from_settings(settings, provider="openai_cloud")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "openai_api_key is required" in str(exc)
