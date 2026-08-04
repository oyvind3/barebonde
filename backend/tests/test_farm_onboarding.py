import os

from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("COSMOS_DB_CONNECTION_STRING", "not-used-in-unit-tests")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("IDENTITY_HMAC_KEY", "test-identity-hmac-key")

from app.api.dependencies import farm_access, identity as identity_dependency
from app.api.routes import farms
from app.core.permissions import permissions_for_role
from app.services.membership_service import InactiveMembershipError, MembershipNotFoundError, membership_id


def make_client() -> TestClient:
    app = FastAPI()
    app.include_router(farms.router, prefix="/api/farms")
    return TestClient(app)


class FarmStore:
    def __init__(self):
        self.items = {}

    def create_item(self, item):
        if item["id"] in self.items:
            raise farms.exceptions.CosmosResourceExistsError(message="exists", response=None)
        self.items[item["id"]] = dict(item)

    def upsert_item(self, item):
        self.items[item["id"]] = dict(item)


class State:
    def __init__(self):
        self.farms = FarmStore()
        self.memberships = {}


def configure_authenticated_user(monkeypatch, state, *, user_id="user-123"):
    class FakeSessionService:
        def get_session(self, _raw_token):
            return (
                {"id": "session-1", "expires_at": "2027-01-01T00:00:00+00:00"},
                {"user_id": user_id, "email": "ola@example.com", "status": "active"},
            )

        def csrf_token(self, _raw_token):
            return "csrf-token"

    class FakeMembershipService:
        def __init__(self, *_, farms_container=None, **__):
            self.farms = farms_container or state.farms

        def get_farm_by_org_number(self, org_number):
            return next((item for item in state.farms.items.values() if item.get("org_number") == org_number), None)

        def get_farm(self, farm_id):
            item = state.farms.items.get(farm_id)
            return dict(item) if item else None

        def get_active_membership(self, *, farm_id, user_id):
            membership = state.memberships.get(membership_id(farm_id, user_id))
            if membership is None:
                raise MembershipNotFoundError()
            if membership.get("membership_status", "active") != "active" or not membership.get("farm_role"):
                raise InactiveMembershipError()
            return dict(membership)

        def create_owner_membership(self, *, farm, user_id):
            identifier = membership_id(farm["id"], user_id)
            existing = state.memberships.get(identifier)
            if existing:
                return dict(existing)
            membership = {
                "id": identifier,
                "farm_id": farm["id"],
                "user_id": user_id,
                "farm_role": "owner",
                "role": "owner",
                "membership_status": "active",
                "farm_name": farm["name"],
                "org_number": farm["org_number"],
            }
            state.memberships[identifier] = membership
            return dict(membership)

        def permissions_for_membership(self, membership):
            return permissions_for_role(membership.get("farm_role"))

        def list_active_memberships_for_user(self, listed_user_id):
            return [
                dict(item) for item in state.memberships.values()
                if item["user_id"] == listed_user_id and item.get("membership_status", "active") == "active"
            ]

        def list_members_for_farm(self, farm_id):
            return [dict(item) for item in state.memberships.values() if item["farm_id"] == farm_id]

    monkeypatch.setattr(identity_dependency, "SessionService", FakeSessionService)
    monkeypatch.setattr(farm_access, "MembershipService", FakeMembershipService)
    monkeypatch.setattr(farms, "MembershipService", FakeMembershipService)
    monkeypatch.setattr(farms, "get_farms_container", lambda: state.farms)
    monkeypatch.setattr(farms, "_write_audit_event", lambda *_: None)


async def brreg_farm(_org_number):
    return {
        "name": "Solberg gård",
        "address": "Gårdsveien 14",
        "municipality": "Nes",
        "organization_form": "ENK",
        "industry_code": "Dyrking av korn",
    }


def valid_payload(**overrides):
    payload = {
        "name": "Solberg gård",
        "org_number": "123456789",
        "primary_farm_type": "plante",
        "production_types": ["korn", "grovfor", "korn"],
        "farm_size_range": "50_199",
        "team_size": "2_5",
        "onboarding_goals": ["regnskap", "frister"],
    }
    payload.update(overrides)
    return payload


def authenticated_post(client, path, *, headers=None, **kwargs):
    request_headers = {"X-CSRF-Token": "csrf-token"}
    request_headers.update(headers or {})
    return client.post(path, cookies={"barebonde_session": "session-cookie"}, headers=request_headers, **kwargs)


def test_post_farm_requires_session_and_csrf(monkeypatch):
    state = State()
    configure_authenticated_user(monkeypatch, state)
    monkeypatch.setattr(farms.brreg_service, "lookup_org", brreg_farm)
    client = make_client()

    assert client.post("/api/farms", json=valid_payload()).status_code == 401
    assert client.post("/api/farms", cookies={"barebonde_session": "session-cookie"}, json=valid_payload()).status_code == 403


def test_create_farm_derives_owner_from_session_ignores_onboarding_header_and_retries(monkeypatch):
    state = State()
    configure_authenticated_user(monkeypatch, state)
    monkeypatch.setattr(farms.brreg_service, "lookup_org", brreg_farm)
    client = make_client()

    first = authenticated_post(
        client,
        "/api/farms",
        headers={"X-Onboarding-User-Id": "attacker"},
        json=valid_payload(),
    )
    second = authenticated_post(client, "/api/farms", json=valid_payload())

    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"] == "farm:123456789"
    owner = state.memberships[membership_id("farm:123456789", "user-123")]
    assert owner["farm_role"] == "owner"
    assert all(item["user_id"] != "attacker" for item in state.memberships.values())
    assert "demo-user" not in str(state.memberships)


def test_existing_farm_without_membership_is_not_disclosed(monkeypatch):
    state = State()
    state.farms.items["farm:123456789"] = {"id": "farm:123456789", "org_number": "123456789", "name": "Andres gård", "farm_status": "active"}
    configure_authenticated_user(monkeypatch, state)
    client = make_client()

    response = authenticated_post(client, "/api/farms", json=valid_payload())

    assert response.status_code == 404
    assert state.memberships == {}


def test_authorized_retry_completes_a_provisioning_farm(monkeypatch):
    state = State()
    state.farms.items["farm:123456789"] = {
        "id": "farm:123456789",
        "org_number": "123456789",
        "name": "Solberg gård",
        "farm_status": "provisioning",
        "created_by_user_id": "user-123",
    }
    configure_authenticated_user(monkeypatch, state)
    client = make_client()

    response = authenticated_post(client, "/api/farms", json=valid_payload())

    assert response.status_code == 200
    assert state.farms.items["farm:123456789"]["farm_status"] == "active"
    assert membership_id("farm:123456789", "user-123") in state.memberships


def test_get_list_patch_and_members_are_tenant_isolated(monkeypatch):
    state = State()
    state.farms.items.update(
        {
            "farm-a": {"id": "farm-a", "org_number": "111111111", "name": "Min gård", "farm_status": "active"},
            "farm-b": {"id": "farm-b", "org_number": "222222222", "name": "Annen gård", "farm_status": "active"},
        }
    )
    state.memberships[membership_id("farm-a", "user-123")] = {
        "id": membership_id("farm-a", "user-123"), "farm_id": "farm-a", "user_id": "user-123", "farm_role": "manager", "membership_status": "active"
    }
    state.memberships[membership_id("farm-a", "staff-1")] = {
        "id": membership_id("farm-a", "staff-1"), "farm_id": "farm-a", "user_id": "staff-1", "farm_role": "staff", "membership_status": "active"
    }
    state.memberships[membership_id("farm-b", "other-user")] = {
        "id": membership_id("farm-b", "other-user"), "farm_id": "farm-b", "user_id": "other-user", "farm_role": "owner", "membership_status": "active"
    }
    configure_authenticated_user(monkeypatch, state)
    client = make_client()
    cookies = {"barebonde_session": "session-cookie"}

    listed = client.get("/api/farms", cookies=cookies)
    mine = client.get("/api/farms/farm-a", cookies=cookies)
    other = client.get("/api/farms/farm-b", cookies=cookies)
    updated = client.patch("/api/farms/farm-a", cookies=cookies, headers={"X-CSRF-Token": "csrf-token"}, json={"name": "Nytt navn"})
    members = client.get("/api/farms/farm-a/members", cookies=cookies)

    assert [farm["id"] for farm in listed.json()] == ["farm-a"]
    assert mine.status_code == 200
    assert other.status_code == 404
    assert updated.status_code == 200 and updated.json()["name"] == "Nytt navn"
    assert members.status_code == 200 and {member["user_id"] for member in members.json()} == {"user-123", "staff-1"}


def test_staff_cannot_patch_even_with_csrf(monkeypatch):
    state = State()
    state.farms.items["farm-a"] = {"id": "farm-a", "org_number": "111111111", "name": "Min gård", "farm_status": "active"}
    state.memberships[membership_id("farm-a", "user-123")] = {
        "id": membership_id("farm-a", "user-123"), "farm_id": "farm-a", "user_id": "user-123", "farm_role": "staff", "membership_status": "active"
    }
    configure_authenticated_user(monkeypatch, state)

    response = make_client().patch("/api/farms/farm-a", cookies={"barebonde_session": "session-cookie"}, headers={"X-CSRF-Token": "csrf-token"}, json={"name": "Ikke lov"})

    assert response.status_code == 403


def test_manual_farm_keeps_membership_control_and_brreg_errors_are_safe(monkeypatch):
    state = State()
    configure_authenticated_user(monkeypatch, state)
    client = make_client()

    manual = authenticated_post(client, "/api/farms", headers={"Idempotency-Key": "manual-retry"}, json=valid_payload(name="Hjemmegården", org_number="", manual_entry=True))
    assert manual.status_code == 200
    assert manual.json()["org_number"].startswith("manual-")

    async def unavailable(_org_number):
        raise RuntimeError("BRREG unavailable")

    monkeypatch.setattr(farms.brreg_service, "lookup_org", unavailable)
    unavailable_response = authenticated_post(client, "/api/farms", json=valid_payload(org_number="333333333"))
    assert unavailable_response.status_code == 503
