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


def test_onboarding_confirmation_link_returns_to_farm_setup(monkeypatch):
    sent = []

    class FakeChallengeService:
        def create_email_registration_challenge(self, **_):
            return "one-time-token"

    async def fake_send(**kwargs):
        sent.append(kwargs)

    monkeypatch.setattr(auth, "ChallengeService", FakeChallengeService)
    monkeypatch.setattr(auth, "_get_plunk_config", lambda: ("sk_test", "post@example.com", "Barebonde", None, "url"))
    monkeypatch.setattr(auth, "_send_plunk_email", fake_send)

    asyncio.run(auth._send_confirmation_email("ola@example.com", "Ola"))

    assert "https://barebonde.no/farm/setup?token=one-time-token" in sent[0]["body"]


def test_legacy_registration_entry_does_not_create_a_user_before_verification(monkeypatch):
    sent = []

    async def send_registration_link(*args, **_):
        sent.append(args)

    monkeypatch.setattr(auth, "_send_confirmation_email", send_registration_link)

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
    assert response.json()["user_id"] == ""
    assert sent == [("ola@example.com", "Ola")]


def test_magic_link_verify_sets_cookie_after_single_use_challenge(monkeypatch):
    class FakeChallengeService:
        def consume_email_challenge(self, token):
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


def test_login_request_returns_account_not_found_without_sending_email(monkeypatch):
    class FakeChallengeService:
        def create_email_login_challenge(self, **_):
            raise auth.IdentityError("account_not_found")

    monkeypatch.setattr(auth, "ChallengeService", FakeChallengeService)
    monkeypatch.setattr(auth, "_get_plunk_config", lambda: ("sk_test", "post@example.com", "Barebonde", None, "url"))

    response = make_client().post("/email/request", json={"email": "ny@example.com"})

    assert response.status_code == 404
    assert response.json()["detail"] == "account_not_found"


def test_registration_request_creates_only_a_registration_challenge(monkeypatch):
    calls = []

    class FakeChallengeService:
        def create_email_registration_challenge(self, **kwargs):
            calls.append(kwargs)
            return "registration-token"

    async def fake_send(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(auth, "ChallengeService", FakeChallengeService)
    monkeypatch.setattr(auth, "_get_plunk_config", lambda: ("sk_test", "post@example.com", "Barebonde", None, "url"))
    monkeypatch.setattr(auth, "_send_plunk_email", fake_send)

    response = make_client().post("/register/email/request", json={"email": "ny@example.com"})

    assert response.status_code == 200
    assert calls[0] == {"email": "ny@example.com"}
    assert "registration-token" in calls[1]["body"]


def test_me_is_limited_to_identity_and_session_data(monkeypatch):
    class FakeSessionService:
        def get_session(self, raw_token):
            assert raw_token == "browser-cookie"
            return session_document(), user_document()

        def csrf_token(self, _raw_token):
            return "csrf-public-value"

    class FakeMembershipService:
        def list_active_memberships_for_user(self, _user_id):
            return []

    monkeypatch.setattr(identity_dependency, "SessionService", FakeSessionService)
    monkeypatch.setattr(me, "SessionService", FakeSessionService)
    monkeypatch.setattr(me, "MembershipService", FakeMembershipService)

    response = make_client(include_me=True).get("/me", cookies={"barebonde_session": "browser-cookie"})

    assert response.status_code == 200
    assert response.json()["memberships"] == []
    assert response.json()["active_farm"] is None
    assert response.json()["subscription"] is None
    assert response.json()["entitlements"] == {}


def test_me_returns_only_active_memberships_and_validates_active_farm_preference(monkeypatch):
    class FakeSessionService:
        def get_session(self, _raw_token):
            return session_document(), user_document()

        def csrf_token(self, _raw_token):
            return "csrf-public-value"

    class FakeMembershipService:
        def list_active_memberships_for_user(self, user_id):
            assert user_id == "internal-user-id"
            return [
                {
                    "farm_id": "farm-a",
                    "farm_name": "Alfa gård",
                    "org_number": "111111111",
                    "farm_role": "owner",
                    "membership_status": "active",
                },
                {
                    "farm_id": "farm-b",
                    "farm_name": "Beta gård",
                    "org_number": "222222222",
                    "farm_role": "staff",
                    "membership_status": "active",
                },
            ]

    class FakeSubscriptionService:
        def ensure_free_subscription(self, *, farm_id, actor_user_id=None):
            return type(
                "EnsuredSubscription",
                (),
                {
                    "subscription": {
                        "id": f"subscription:{farm_id}",
                        "farm_id": farm_id,
                        "plan_code": "free",
                        "plan_version": "2026-08",
                        "subscription_status": "active",
                        "started_at": "2026-08-04T00:00:00+00:00",
                        "current_period_start": None,
                        "current_period_end": None,
                        "trial_ends_at": None,
                        "grace_period_ends_at": None,
                        "cancel_at_period_end": False,
                        "canceled_at": None,
                    },
                    "created": False,
                },
            )()

    monkeypatch.setattr(identity_dependency, "SessionService", FakeSessionService)
    monkeypatch.setattr(me, "SessionService", FakeSessionService)
    monkeypatch.setattr(me, "MembershipService", FakeMembershipService)
    monkeypatch.setattr(me, "SubscriptionService", FakeSubscriptionService)
    client = make_client(include_me=True)
    cookies = {"barebonde_session": "browser-cookie"}

    selected = client.get("/me?active_farm_id=farm-b", cookies=cookies)
    invalid = client.get("/me?active_farm_id=farm-not-a-member", cookies=cookies)

    assert [item["farm"]["id"] for item in selected.json()["memberships"]] == ["farm-a", "farm-b"]
    assert selected.json()["active_farm"]["id"] == "farm-b"
    assert invalid.json()["active_farm"]["id"] == "farm-a"


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
