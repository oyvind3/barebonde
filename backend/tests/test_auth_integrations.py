import asyncio
import os

from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("COSMOS_DB_CONNECTION_STRING", "not-used-in-unit-tests")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

from app.api.routes import auth
from app.db.cosmos_models import User


def make_client() -> TestClient:
    app = FastAPI()
    app.include_router(auth.router)
    return TestClient(app)


def clear_plunk_environment(monkeypatch):
    for key in (
        "PLUNK_SECRET_KEY",
        "PLUNK_SECRET_API_KEY",
        "PLUNK_API_TOKEN",
        "PLUNK_PUBLIC_API_KEY",
        "PLUNK_FROM_EMAIL",
        "PLUNK_FROM_NAME",
        "PLUNK_REPLY_TO_EMAIL",
        "PLUNK_API_URL",
    ):
        monkeypatch.delenv(key, raising=False)


def test_resend_reports_missing_plunk_configuration(monkeypatch):
    clear_plunk_environment(monkeypatch)

    response = make_client().post(
        "/resend-confirmation",
        json={"email": "ola@example.com", "first_name": "Ola"},
    )

    assert response.status_code == 503
    assert "secret key" in response.json()["detail"]


def test_plunk_sender_uses_secret_key_verified_sender_and_current_endpoint(monkeypatch):
    clear_plunk_environment(monkeypatch)
    monkeypatch.setenv("PLUNK_SECRET_API_KEY", "sk_test_key")
    monkeypatch.setenv("PLUNK_FROM_EMAIL", "post@example.com")
    calls = []

    class Response:
        status_code = 200

        def json(self):
            return {"success": True}

    class AsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return Response()

    monkeypatch.setattr(auth.httpx, "AsyncClient", AsyncClient)
    asyncio.run(auth._send_plunk_email(to="ola@example.com", subject="Hei", body="<p>Hei</p>"))

    assert calls[0][0] == "https://next-api.useplunk.com/v1/send"
    assert calls[0][1]["headers"]["Authorization"] == "Bearer sk_test_key"
    assert calls[0][1]["json"]["from"] == {"email": "post@example.com", "name": "Barebonde"}


def test_google_config_is_available_at_runtime(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id.apps.googleusercontent.com")

    response = make_client().get("/google/config")

    assert response.status_code == 200
    assert response.json() == {"client_id": "client-id.apps.googleusercontent.com"}


def test_google_auth_links_google_identity_to_existing_profile(monkeypatch):
    stored = []
    existing = {
        "id": "barebonde-user-id",
        "email": "ola@example.com",
        "better_auth_id": "user_ola@example.com",
        "first_name": "Ola",
        "last_name": "Nordmann",
        "phone_number": "+4791234567",
    }

    class UsersContainer:
        def query_items(self, **_):
            return [existing]

        def upsert_item(self, item):
            stored.append(item)

    async def verified_token(_):
        return {
            "sub": "google-user-id",
            "email": "ola@example.com",
            "given_name": "Ola",
            "family_name": "Nordmann",
        }

    monkeypatch.setattr(auth, "get_users_container", lambda: UsersContainer())
    monkeypatch.setattr(auth, "verify_google_token", verified_token)

    response = make_client().post("/google", json={"token": "valid-google-token"})

    assert response.status_code == 200
    assert response.json()["last_name"] == "Nordmann"
    assert response.json()["user_id"] == "barebonde-user-id"
    assert stored[0]["google_id"] == "google-user-id"


def test_google_auth_requires_completed_profile(monkeypatch):
    class UsersContainer:
        def query_items(self, **_):
            return []

    async def verified_token(_):
        return {
            "sub": "google-user-id",
            "email": "ola@example.com",
            "given_name": "Ola",
            "family_name": "Nordmann",
        }

    monkeypatch.setattr(auth, "get_users_container", lambda: UsersContainer())
    monkeypatch.setattr(auth, "verify_google_token", verified_token)

    response = make_client().post("/google", json={"token": "valid-google-token"})

    assert response.status_code == 404
    assert "gårdsoppsettet" in response.json()["detail"]


def test_user_model_serializes_google_identity():
    user = User(email="ola@example.com", better_auth_id="google-1", google_id="google-1")

    assert user.to_dict()["google_id"] == "google-1"


def test_google_onboarding_persists_phone_only_after_final_registration(monkeypatch):
    stored = []

    class UsersContainer:
        def query_items(self, **_):
            return []

        def upsert_item(self, item):
            stored.append(item)

    async def verified_token(_):
        return {
            "sub": "google-user-id",
            "email": "ola@example.com",
            "given_name": "Ola",
            "family_name": "Nordmann",
            "email_verified": True,
        }

    monkeypatch.setattr(auth, "get_users_container", lambda: UsersContainer())
    monkeypatch.setattr(auth, "verify_google_token", verified_token)

    verified = make_client().post("/google/verify", json={"token": "valid-google-token"})
    assert verified.status_code == 200
    assert stored == []

    created = make_client().post(
        "/register",
        json={
            "first_name": "ignored",
            "last_name": "ignored",
            "email": "ignored@example.com",
            "phone_number": "912 34 567",
            "google_token": "valid-google-token",
            "address": "Gårdsveien 14",
            "onboarding_role": "owner",
        },
    )

    assert created.status_code == 200
    assert created.json()["email"] == "ola@example.com"
    assert created.json()["phone_number"] == "+4791234567"
    assert stored[0]["phone_number"] == "+4791234567"
    assert stored[0]["address"] == "Gårdsveien 14"
    assert stored[0]["google_id"] == "google-user-id"
    assert stored[0]["onboarding_role"] == "owner"


def test_register_rejects_phone_number_without_country_code_or_norwegian_format():
    response = make_client().post(
        "/register",
        json={
            "first_name": "Ola",
            "last_name": "Nordmann",
            "email": "ola@example.com",
            "password": "hemmelig-passord",
            "phone_number": "123",
        },
    )

    assert response.status_code == 422
    assert "telefonnummer" in str(response.json()).lower()
