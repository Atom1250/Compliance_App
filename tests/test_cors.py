from fastapi.testclient import TestClient

from apps.api.main import app


def test_cors_preflight_for_company_endpoint() -> None:
    client = TestClient(app)

    response = client.options(
        "/companies",
        headers={
            "Origin": "http://127.0.0.1:3001",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-api-key,x-tenant-id",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:3001"
