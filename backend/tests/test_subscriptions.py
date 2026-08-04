import os
from types import SimpleNamespace

import pytest
from azure.cosmos import exceptions
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("COSMOS_DB_CONNECTION_STRING", "not-used-in-unit-tests")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("IDENTITY_HMAC_KEY", "test-identity-hmac-key")

from app.api.dependencies import entitlements as entitlement_dependency
from app.api.dependencies import farm_access, identity as identity_dependency
from app.api.routes import accounting, me, subscriptions
from app.services.entitlement_service import get_effective_entitlements, subscription_allows
from app.services.membership_service import InactiveMembershipError, MembershipNotFoundError
from app.services.subscription_service import SubscriptionService, SubscriptionUnavailableError
from app.subscriptions.plans import ACTIVE_PLAN_VERSION, PLAN_CATALOG, get_plan


class MemorySubscriptionContainer:
    def __init__(self, items=None):
        self.items = {item["id"]: dict(item) for item in (items or [])}
        self.last_partition_key = None
        self.fail_reads = False
        self.conflict_once = False

    def read_item(self, *, item, partition_key):
        self.last_partition_key = partition_key
        if self.fail_reads:
            raise RuntimeError("container unavailable")
        document = self.items.get(item)
        if document is None or document.get("farm_id") != partition_key:
            raise exceptions.CosmosResourceNotFoundError(message="missing", response=None)
        return dict(document)

    def create_item(self, item):
        if self.conflict_once:
            self.conflict_once = False
            self.items[item["id"]] = dict(item)
            raise exceptions.CosmosResourceExistsError(message="conflict", response=None)
        if item["id"] in self.items:
            raise exceptions.CosmosResourceExistsError(message="exists", response=None)
        self.items[item["id"]] = dict(item)
        return dict(item)


class MemoryAuditContainer:
    def __init__(self):
        self.items = []

    def create_item(self, item):
        self.items.append(dict(item))
        return item


def subscription(farm_id="farm-a", *, plan_code="free", status="active", version=ACTIVE_PLAN_VERSION):
    return {
        "id": f"subscription:{farm_id}",
        "type": "subscription",
        "farm_id": farm_id,
        "plan_code": plan_code,
        "plan_version": version,
        "subscription_status": status,
        "started_at": "2026-08-04T00:00:00+00:00",
        "current_period_start": None,
        "current_period_end": None,
        "trial_ends_at": None,
        "grace_period_ends_at": None,
        "cancel_at_period_end": False,
        "canceled_at": None,
        "version": 1,
        "created_at": "2026-08-04T00:00:00+00:00",
        "updated_at": "2026-08-04T00:00:00+00:00",
    }


def test_plan_catalogue_is_versioned_immutable_and_fails_closed():
    plans = PLAN_CATALOG[ACTIVE_PLAN_VERSION]

    assert set(plans) == {"free", "standard", "premium"}
    assert plans["free"].entitlements["reports.advanced.enabled"] is False
    assert plans["standard"].entitlements["reports.advanced.enabled"] is True
    assert plans["premium"].entitlements["reports.advanced.enabled"] is True
    assert get_plan("unknown", "free") is None
    assert get_plan(ACTIVE_PLAN_VERSION, "unknown") is None
    with pytest.raises(TypeError):
        PLAN_CATALOG["other"] = plans  # type: ignore[index]
    with pytest.raises(TypeError):
        plans["free"].entitlements["reports.advanced.enabled"] = True  # type: ignore[index]


def test_effective_entitlements_and_status_policy_fail_closed():
    free = subscription()

    assert get_effective_entitlements(free)["reports.basic.enabled"] is True
    assert get_effective_entitlements(free)["reports.advanced.enabled"] is False
    assert get_effective_entitlements(subscription(plan_code="unknown")) == {}
    assert get_effective_entitlements(subscription(version="missing")) == {}
    assert subscription_allows(subscription(status="active"), "mutate") is True
    assert subscription_allows(subscription(status="grace_period"), "read") is True
    assert subscription_allows(subscription(status="grace_period"), "mutate") is False
    assert subscription_allows(subscription(status="suspended"), "read") is False


def test_subscription_service_uses_deterministic_point_reads_and_never_overwrites_existing_plan():
    container = MemorySubscriptionContainer([subscription(plan_code="premium")])
    audits = MemoryAuditContainer()
    service = SubscriptionService(subscriptions_container=container, audit_logs_container=audits)

    existing = service.ensure_free_subscription("farm-a", actor_user_id="user-a")
    created = service.ensure_free_subscription("farm-b", actor_user_id="user-a")

    assert existing.created is False
    assert existing.subscription["plan_code"] == "premium"
    assert created.created is True
    assert created.subscription["id"] == "subscription:farm-b"
    assert container.last_partition_key == "farm-b"
    assert container.items["subscription:farm-b"]["plan_code"] == "free"
    assert [item["event_type"] for item in audits.items] == ["FreePlanAssigned"]


def test_subscription_service_handles_conflict_and_unavailable_container_safely():
    container = MemorySubscriptionContainer()
    container.conflict_once = True
    service = SubscriptionService(subscriptions_container=container, audit_logs_container=MemoryAuditContainer())

    result = service.ensure_free_subscription("farm-a")
    assert result.created is False
    assert result.subscription["plan_code"] == "free"

    unavailable = MemorySubscriptionContainer()
    unavailable.fail_reads = True
    with pytest.raises(SubscriptionUnavailableError):
        SubscriptionService(subscriptions_container=unavailable, audit_logs_container=MemoryAuditContainer()).get_subscription("farm-a")


class SubscriptionRouteState:
    def __init__(self, *, role="owner", plan_code="free", status="active", has_membership=True):
        self.role = role
        self.has_membership = has_membership
        self.farms = {
            "farm-a": {"id": "farm-a", "name": "Min gård", "org_number": "111111111", "farm_status": "active"},
            "farm-b": {"id": "farm-b", "name": "Annen gård", "org_number": "222222222", "farm_status": "active"},
        }
        self.memberships = {
            "farm-a": {
                "farm_id": "farm-a",
                "user_id": "user-a",
                "farm_role": role,
                "membership_status": "active",
                "farm_name": "Min gård",
                "org_number": "111111111",
            }
        } if has_membership else {}
        self.subscriptions = {"farm-a": subscription("farm-a", plan_code=plan_code, status=status)}
        self.ensured_farms = []


class EmptyTransactions:
    def query_items(self, **_):
        return []


def make_client(monkeypatch, state: SubscriptionRouteState) -> TestClient:
    class FakeSessionService:
        def get_session(self, raw_token):
            assert raw_token == "session-cookie"
            return (
                {"id": "session-a", "created_at": "2026-08-04T00:00:00+00:00", "expires_at": "2027-08-04T00:00:00+00:00"},
                {"user_id": "user-a", "email": "ola@example.com", "status": "active"},
            )

        def csrf_token(self, _raw_token):
            return "csrf-token"

    class FakeMembershipService:
        def get_active_membership(self, *, farm_id, user_id):
            membership = state.memberships.get(farm_id)
            if membership is None or user_id != "user-a":
                raise MembershipNotFoundError()
            if membership.get("membership_status") != "active" or not membership.get("farm_role"):
                raise InactiveMembershipError()
            return dict(membership)

        def get_farm(self, farm_id):
            return state.farms.get(farm_id)

        def permissions_for_membership(self, membership):
            from app.core.permissions import permissions_for_role
            return permissions_for_role(membership.get("farm_role"))

        def list_active_memberships_for_user(self, user_id):
            return [dict(item) for item in state.memberships.values() if item["user_id"] == user_id]

    class FakeSubscriptionService:
        def ensure_free_subscription(self, *, farm_id, actor_user_id=None):
            state.ensured_farms.append(farm_id)
            existing = state.subscriptions.get(farm_id)
            if existing is None:
                existing = subscription(farm_id)
                state.subscriptions[farm_id] = existing
                return SimpleNamespace(subscription=dict(existing), created=True)
            return SimpleNamespace(subscription=dict(existing), created=False)

    monkeypatch.setattr(identity_dependency, "SessionService", FakeSessionService)
    monkeypatch.setattr(me, "SessionService", FakeSessionService)
    monkeypatch.setattr(farm_access, "MembershipService", FakeMembershipService)
    monkeypatch.setattr(me, "MembershipService", FakeMembershipService)
    monkeypatch.setattr(me, "SubscriptionService", FakeSubscriptionService)
    monkeypatch.setattr(subscriptions, "SubscriptionService", FakeSubscriptionService)
    monkeypatch.setattr(entitlement_dependency, "SubscriptionService", FakeSubscriptionService)
    monkeypatch.setattr(accounting, "get_transactions_container", EmptyTransactions)

    app = FastAPI()
    app.include_router(me.router, prefix="/api")
    app.include_router(subscriptions.router, prefix="/api")
    app.include_router(accounting.router)
    return TestClient(app)


def auth_cookies():
    return {"barebonde_session": "session-cookie"}


def test_me_lazily_returns_only_active_farm_subscription_and_safe_fields(monkeypatch):
    state = SubscriptionRouteState(plan_code="standard")
    client = make_client(monkeypatch, state)

    response = client.get("/api/me", cookies=auth_cookies())

    assert response.status_code == 200
    payload = response.json()
    assert payload["subscription"]["plan_code"] == "standard"
    assert payload["entitlements"]["reports.advanced.enabled"] is True
    assert state.ensured_farms == ["farm-a"]
    assert "payment_provider" not in payload["subscription"]
    assert "external_customer_id" not in payload["subscription"]


def test_me_without_active_farm_returns_null_subscription(monkeypatch):
    state = SubscriptionRouteState(has_membership=False)
    client = make_client(monkeypatch, state)

    response = client.get("/api/me", cookies=auth_cookies())

    assert response.status_code == 200
    assert response.json()["subscription"] is None
    assert response.json()["entitlements"] == {}
    assert state.ensured_farms == []


def test_subscription_apis_are_tenant_scoped_and_lazy_initialize(monkeypatch):
    state = SubscriptionRouteState()
    del state.subscriptions["farm-a"]
    client = make_client(monkeypatch, state)

    plans = client.get("/api/plans")
    subscription_response = client.get("/api/farms/farm-a/subscription", cookies=auth_cookies())
    entitlements_response = client.get("/api/farms/farm-a/entitlements", cookies=auth_cookies())
    hidden = client.get("/api/farms/farm-b/subscription", cookies=auth_cookies())

    assert plans.status_code == 200
    assert {plan["plan_code"] for plan in plans.json()["plans"]} == {"free", "standard", "premium"}
    assert subscription_response.status_code == 200
    assert subscription_response.json()["plan_code"] == "free"
    assert entitlements_response.status_code == 200
    assert entitlements_response.json()["entitlements"]["reports.basic.enabled"] is True
    assert hidden.status_code == 404


def test_subscription_read_requires_permission_but_entitlements_need_only_membership(monkeypatch):
    state = SubscriptionRouteState(role="staff")
    client = make_client(monkeypatch, state)

    assert client.get("/api/farms/farm-a/subscription", cookies=auth_cookies()).status_code == 403
    assert client.get("/api/farms/farm-a/entitlements", cookies=auth_cookies()).status_code == 200


@pytest.mark.parametrize(
    ("role", "plan_code", "status", "expected", "message"),
    [
        ("owner", "free", "active", 403, "ikke inkludert"),
        ("manager", "standard", "active", 200, ""),
        ("staff", "premium", "active", 403, "ikke tilgang"),
        ("manager", "premium", "suspended", 403, "gir ikke tilgang"),
    ],
)
def test_advanced_report_requires_permission_then_subscription(monkeypatch, role, plan_code, status, expected, message):
    state = SubscriptionRouteState(role=role, plan_code=plan_code, status=status)
    client = make_client(monkeypatch, state)

    response = client.get("/api/farms/farm-a/reports/liquidity", cookies=auth_cookies())

    assert response.status_code == expected
    if message:
        assert message in response.json()["detail"]
    if role == "staff":
        assert state.ensured_farms == []


def test_basic_report_remains_available_on_free_and_non_membership_is_hidden(monkeypatch):
    free_state = SubscriptionRouteState(role="owner", plan_code="free")
    free_client = make_client(monkeypatch, free_state)
    assert free_client.get("/api/farms/farm-a/reports/monthly", cookies=auth_cookies()).status_code == 200

    no_membership_state = SubscriptionRouteState(has_membership=False)
    no_membership_client = make_client(monkeypatch, no_membership_state)
    assert no_membership_client.get("/api/farms/farm-a/reports/liquidity", cookies=auth_cookies()).status_code == 404
    assert no_membership_state.ensured_farms == []
