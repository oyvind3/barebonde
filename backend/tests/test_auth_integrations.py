import asyncio
import os

from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("COSMOS_DB_CONNECTION_STRING", "not-used-in-unit-tests")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("IDENTITY_HMAC_KEY", "test-identity-hmac-key")

from app.api.dependencies import identity as identity_dependency
from app.api.routes import auth, me


def make_client(*, include_me=False):
    app = FastAPI()
    app.include_router(auth.router)
    if include_me:
        app.include_router(me.router)
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


def session_document():
    return {
        "id": "session-hmac-id",
        "created_at": "2026-01-01T00:00:00+00:00",
        "last_seen_at": "2026-01-01T00:00:00+00:00",
        "expires_at": "2026-01-08T00:00:00+00:00",
    }


def user_document():
    return {
        "id": "internal-user-id",
        "user_id": "internal-user-id",
        "better_auth_id": "user_internal-user-id",
        "email": "ola@example.com",
        "first_name": "Ola",
        "last_name": "Nordmann",
        "status": "active",
    }


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


def test_google_auth_creates_an_opaque_cookie_and_never_returns_the_session_secret(monkeypatch):
    class FakeIdentityService:
        def resolve_google_identity(self, **_):
            return user_document()

    class FakeSessionService:
        def create_session(self, _user):
            return "raw-browser-secret", session_document()

        def csrf_token(self, raw_token):
            assert raw_token == "raw-browser-secret"
            return "csrf-public-value"

    async def verified_token(_):
        return {
            "sub": "google-subject",
            "email": "ola@gmail.com",
            "email_verified": True,
            "given_name": "Ola",
            "family_name": "Nordmann",
        }

    monkeypatch.setattr(auth, "IdentityService", FakeIdentityService)
    monkeypatch.setattr(auth, "SessionService", FakeSessionService)
    monkeypatch.setattr(auth, "verify_google_token", verified_token)

    response = make_client().post("/google", json={"token": "valid-google-token"})

    assert response.status_code == 200
    assert response.json()["user_id"] == "internal-user-id"
    assert response.json()["csrf_token"] == "csrf-public-value"
    assert "raw-browser-secret" not in response.text
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "barebonde_session=raw-browser-secret" in response.headers["set-cookie"]


def test_google_auth_requires_a_verified_google_email(monkeypatch):
    async def unverified_token(_):
        return {"sub": "google-subject", "email": "ola@example.com", "email_verified": False}

    monkeypatch.setattr(auth, "verify_google_token", unverified_token)

    response = make_client().post("/google", json={"token": "invalid-google-token"})

    assert response.status_code == 401
    assert "bekreftet" in response.json()["detail"]


def test_passwordless_onboarding_profile_keeps_phone_number_without_accepting_a_password(monkeypatch):
    stored = []

    class UsersContainer:
        def upsert_item(self, item):
            stored.append(dict(item))

    class FakeIdentityService:
        users = UsersContainer()

        def resolve_email_identity(self, **_):
            return user_document()

    async def send_login_link(*_, **__):
        return None

    monkeypatch.setattr(auth, "IdentityService", FakeIdentityService)
    monkeypatch.setattr(auth, "_send_confirmation_email", send_login_link)

    response = make_client().post(
        "/register",
        json={
            "first_name": "Ola",
            "last_name": "Nordmann",
            "email": "ola@example.com",
            "phone_number": "912 34 567",
        },
    )

    assert response.status_code == 200
    assert response.json()["email_sent"] is True
    assert stored[0]["phone_number"] == "+4791234567"
    assert stored[0]["email_normalized"] == "ola@example.com"


def test_magic_link_verify_sets_cookie_after_single_use_challenge(monkeypatch):
    class FakeChallengeService:
        def consume_email_login_challenge(self, token):
            assert token == "magic-link-token"
            return user_document()

    class FakeSessionService:
        def create_session(self, _user):
            return "raw-browser-secret", session_document()

        def csrf_token(self, _raw_token):
            return "csrf-public-value"

    monkeypatch.setattr(auth, "ChallengeService", FakeChallengeService)
    monkeypatch.setattr(auth, "SessionService", FakeSessionService)

    response = make_client().post("/magic-link/verify", json={"token": "magic-link-token"})

    assert response.status_code == 200
    assert response.json()["message"].startswith("Innlogging")
    assert "httponly" in response.headers["set-cookie"].lower()


def test_me_is_limited_to_identity_and_session_data(monkeypatch):
    class FakeSessionService:
        def get_session(self, raw_token):
            assert raw_token == "browser-cookie"
            return session_document(), user_document()

        def csrf_token(self, _raw_token):
            return "csrf-public-value"

    monkeypatch.setattr(identity_dependency, "SessionService", FakeSessionService)
    monkeypatch.setattr(me, "SessionService", FakeSessionService)

    response = make_client(include_me=True).get("/me", cookies={"barebonde_session": "browser-cookie"})

    assert response.status_code == 200
    assert set(response.json()) == {"user", "session", "csrf_token"}
    assert "farm" not in response.text.lower()
    assert "subscription" not in response.text.lower()


def test_logout_requires_csrf_and_revokes_only_current_session(monkeypatch):
    revocations = []

    class FakeSessionService:
        def get_session(self, _raw_token):
            return session_document(), user_document()

        def csrf_token(self, _raw_token):
            return "csrf-public-value"

        def revoke_session(self, *, user, session_id):
            revocations.append((user["user_id"], session_id))
            return True

    monkeypatch.setattr(identity_dependency, "SessionService", FakeSessionService)
    monkeypatch.setattr(auth, "SessionService", FakeSessionService)
    client = make_client()

    rejected = client.post("/logout", cookies={"barebonde_session": "browser-cookie"})
    accepted = client.post(
        "/logout",
        cookies={"barebonde_session": "browser-cookie"},
        headers={"X-CSRF-Token": "csrf-public-value"},
    )

    assert rejected.status_code == 403
    assert accepted.status_code == 204
    assert revocations == [("internal-user-id", "session-hmac-id")]


def test_session_overview_and_targeted_revocation_are_limited_to_current_user(monkeypatch):
    revocations = []

    class FakeSessionService:
        def get_session(self, _raw_token):
            return session_document(), user_document()

        def csrf_token(self, _raw_token):
            return "csrf-public-value"

        def list_sessions(self, user, _raw_token):
            assert user["user_id"] == "internal-user-id"
            return [{**session_document(), "session_id": "other-session", "current": False}]

        def revoke_session(self, *, user, session_id):
            revocations.append((user["user_id"], session_id))
            return session_id == "other-session"

    monkeypatch.setattr(identity_dependency, "SessionService", FakeSessionService)
    monkeypatch.setattr(auth, "SessionService", FakeSessionService)
    client = make_client()
    cookies = {"barebonde_session": "browser-cookie"}

    overview = client.get("/sessions", cookies=cookies)
    revoked = client.delete(
        "/sessions/other-session", cookies=cookies, headers={"X-CSRF-Token": "csrf-public-value"}
    )

    assert overview.status_code == 200
    assert overview.json()["sessions"][0]["session_id"] == "other-session"
    assert revoked.status_code == 204
    assert revocations == [("internal-user-id", "other-session")]
