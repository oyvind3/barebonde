import os

from fastapi.testclient import TestClient

os.environ.setdefault("COSMOS_DB_CONNECTION_STRING", "not-used-in-unit-tests")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("IDENTITY_HMAC_KEY", "test-identity-hmac-key")

from main import app


def test_production_frontend_preflight_allows_credentials():
    response = TestClient(app).options(
        "/api/auth/magic-link",
        headers={
            "Origin": "https://barebonde.no",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://barebonde.no"
    assert response.headers["access-control-allow-credentials"] == "true"
