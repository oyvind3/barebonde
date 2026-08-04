import os
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("COSMOS_DB_CONNECTION_STRING", "not-used-in-unit-tests")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("IDENTITY_HMAC_KEY", "test-identity-hmac-key")

from app.api.dependencies import identity as identity_dependency
from app.api.routes import onboarding, profile


class State:
    def __init__(self, memberships=None):
        self.user = {"id": "user-a", "user_id": "user-a", "better_auth_id": "user-user-a", "email": "ola@example.no", "email_normalized": "ola@example.no", "first_name": "Ola", "last_name": "Nordmann", "display_name": "Ola Nordmann", "status": "active", "email_verified": True, "preferred_language": "nb", "timezone": "Europe/Oslo", "profile_completed": False}
        self.memberships = memberships or []


def client(monkeypatch, state):
    class Session:
        def get_session(self, token):
            assert token == "cookie"
            return ({"id": "s", "created_at": "2026-01-01", "expires_at": "2027-01-01"}, state.user)
        def csrf_token(self, _): return "csrf"
    class Identity:
        def update_profile(self, _user, updates):
            state.user.update(updates)
            state.user["display_name"] = str(state.user.get("display_name") or "").strip() or f"{state.user.get('first_name','')} {state.user.get('last_name','')}".strip()
            state.user["profile_completed"] = bool(state.user.get("first_name") and state.user.get("last_name") and state.user.get("terms_accepted_at") and state.user.get("privacy_accepted_at"))
            return dict(state.user)
    class Membership:
        def list_active_memberships_for_user(self, user_id):
            assert user_id == "user-a"; return list(state.memberships)
    monkeypatch.setattr(identity_dependency, "SessionService", Session)
    monkeypatch.setattr(profile, "IdentityService", Identity)
    monkeypatch.setattr(profile, "_audit", lambda *_: None)
    monkeypatch.setattr(onboarding, "IdentityService", Identity)
    monkeypatch.setattr(onboarding, "MembershipService", Membership)
    app = FastAPI(); app.include_router(profile.router, prefix="/api"); app.include_router(onboarding.router, prefix="/api")
    return TestClient(app)


def auth_headers(): return {"X-CSRF-Token": "csrf"}
def cookies(): return {"barebonde_session": "cookie"}


def test_profile_requires_session_and_only_updates_allowed_fields(monkeypatch):
    state = State(); api = client(monkeypatch, state)
    assert api.get("/api/profile").status_code == 401
    assert api.patch("/api/profile", cookies=cookies(), json={"first_name": "Kari"}).status_code == 403
    response = api.patch("/api/profile", cookies=cookies(), headers=auth_headers(), json={"first_name": "Kari", "phone_number": "912 34 567", "preferred_language": "en", "user_id": "attacker", "email": "attacker@example.no", "status": "disabled"})
    assert response.status_code == 200
    assert response.json()["first_name"] == "Kari" and response.json()["phone_number"] == "+4791234567"
    assert state.user["user_id"] == "user-a" and state.user["email"] == "ola@example.no" and state.user["status"] == "active"


def test_profile_validates_phone_language_timezone_and_display_name_fallback(monkeypatch):
    state = State(); api = client(monkeypatch, state)
    assert api.patch("/api/profile", cookies=cookies(), headers=auth_headers(), json={"phone_number": "123"}).status_code == 422
    assert api.patch("/api/profile", cookies=cookies(), headers=auth_headers(), json={"preferred_language": "de"}).status_code == 422
    assert api.patch("/api/profile", cookies=cookies(), headers=auth_headers(), json={"timezone": "America/New_York"}).status_code == 422
    response = api.patch("/api/profile", cookies=cookies(), headers=auth_headers(), json={"display_name": ""})
    assert response.status_code == 200 and response.json()["display_name"] == "Ola Nordmann"


def test_onboarding_is_server_derived_and_completion_requires_profile_and_farm(monkeypatch):
    state = State(); api = client(monkeypatch, state)
    initial = api.get("/api/onboarding", cookies=cookies())
    assert initial.status_code == 200 and initial.json()["completed_steps"] == ["identity"]
    assert api.post("/api/onboarding/complete", cookies=cookies(), headers=auth_headers()).status_code == 400
    saved = api.patch("/api/onboarding", cookies=cookies(), headers=auth_headers(), json={"current_step": "interests", "interests": ["bilag", "rapporter"], "accept_terms": True, "accept_privacy": True})
    assert saved.status_code == 200 and saved.json()["interests"] == ["bilag", "rapporter"]
    assert "profile" in saved.json()["completed_steps"]
    assert api.post("/api/onboarding/complete", cookies=cookies(), headers=auth_headers()).status_code == 400


def test_onboarding_completion_is_idempotent_when_profile_and_membership_exist(monkeypatch):
    membership = {"farm_id": "farm-a", "farm_role": "owner", "membership_status": "active"}
    state = State([membership]); state.user.update({"terms_accepted_at": "2026-08-01", "privacy_accepted_at": "2026-08-01"})
    api = client(monkeypatch, state)
    first = api.post("/api/onboarding/complete", cookies=cookies(), headers=auth_headers())
    second = api.post("/api/onboarding/complete", cookies=cookies(), headers=auth_headers())
    assert first.status_code == second.status_code == 200
    assert first.json()["completed"] is True and "farm" in first.json()["completed_steps"]
