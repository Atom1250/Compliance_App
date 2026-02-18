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
