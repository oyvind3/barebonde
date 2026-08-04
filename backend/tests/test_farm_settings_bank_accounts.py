import os

import pytest
from azure.cosmos import exceptions
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("COSMOS_DB_CONNECTION_STRING", "not-used-in-unit-tests")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("IDENTITY_HMAC_KEY", "test-identity-hmac-key")

from app.api.dependencies import farm_access, identity as identity_dependency
from app.api.routes import settings
from app.core.permissions import permissions_for_role


class Container:
    def __init__(self): self.items = {}
    def read_item(self, *, item, partition_key):
        value = self.items.get(item)
        if not value or value.get("farm_id") != partition_key: raise exceptions.CosmosResourceNotFoundError(message="missing", response=None)
        return dict(value)
    def create_item(self, item): self.items[item["id"]] = dict(item); return dict(item)
    def upsert_item(self, item): self.items[item["id"]] = dict(item); return dict(item)
    def query_items(self, *, parameters, **_):
        farm_id = parameters[0]["value"]; return [dict(x) for x in self.items.values() if x.get("farm_id") == farm_id]


def make_client(monkeypatch, role="owner"):
    state = type("State", (), {})(); state.settings = Container(); state.accounts = Container()
    farms = {"farm-a": {"id":"farm-a","name":"A gård","org_number":"111","farm_status":"active"}, "farm-b": {"id":"farm-b","name":"B gård","org_number":"222","farm_status":"active"}}
    class Session:
        def get_session(self, _): return ({"id":"s","expires_at":"2027"}, {"user_id":"user-a","email":"a@example.no","status":"active"})
        def csrf_token(self, _): return "csrf"
    class Membership:
        def get_active_membership(self, *, farm_id, user_id):
            if farm_id != "farm-a" or user_id != "user-a": raise farm_access.MembershipNotFoundError()
            return {"farm_id":farm_id,"user_id":user_id,"farm_role":role,"membership_status":"active"}
        def get_farm(self, farm_id): return farms.get(farm_id)
        def permissions_for_membership(self, m): return permissions_for_role(m["farm_role"])
    monkeypatch.setattr(identity_dependency, "SessionService", Session); monkeypatch.setattr(farm_access, "MembershipService", Membership)
    monkeypatch.setattr(settings, "get_farm_settings_container", lambda: state.settings); monkeypatch.setattr(settings, "get_bank_accounts_container", lambda: state.accounts)
    app=FastAPI(); app.include_router(settings.router,prefix="/api"); return TestClient(app),state

def cookies(): return {"barebonde_session":"cookie"}
def headers(): return {"X-CSRF-Token":"csrf"}

def test_norwegian_account_validation_normalization_and_masking():
    assert settings.normalize_account_number("8601.11.17947") == "86011117947"
    # Regression: syntactically valid Modulus-11 test account from onboarding.
    assert settings.normalize_account_number("18223822459") == "18223822459"
    assert settings.mask_account_number("86011117947") == "**** **** 947"
    with pytest.raises(ValueError): settings.normalize_account_number("123")
    with pytest.raises(ValueError): settings.normalize_account_number("86011117940")

def test_farm_settings_owner_manager_staff_and_cross_tenant(monkeypatch):
    owner,_=make_client(monkeypatch,"owner")
    assert owner.get("/api/farms/farm-a/settings",cookies=cookies()).status_code == 200
    assert owner.patch("/api/farms/farm-a/settings",cookies=cookies(),headers=headers(),json={"payment_terms_days":30,"default_currency":"NOK"}).status_code == 200
    assert owner.get("/api/farms/farm-b/settings",cookies=cookies()).status_code == 404
    manager,_=make_client(monkeypatch,"manager")
    assert manager.patch("/api/farms/farm-a/settings",cookies=cookies(),headers=headers(),json={"city":"Oslo"}).status_code == 200
    staff,_=make_client(monkeypatch,"staff")
    assert staff.get("/api/farms/farm-a/settings",cookies=cookies()).status_code == 403

def test_bank_accounts_are_owner_only_masked_and_tenant_scoped(monkeypatch):
    api,state=make_client(monkeypatch,"owner")
    assert api.post("/api/farms/farm-a/bank-accounts",cookies=cookies(),json={"display_name":"Drift","account_number":"86011117947"}).status_code == 403
    created=api.post("/api/farms/farm-a/bank-accounts",cookies=cookies(),headers=headers(),json={"display_name":"Drift","account_number":"8601 11 17947","is_default":True})
    assert created.status_code == 201 and created.json()["account_number"] == "86011117947"
    listed=api.get("/api/farms/farm-a/bank-accounts",cookies=cookies())
    assert listed.status_code == 200 and "account_number" not in listed.json()[0] and listed.json()[0]["account_number_masked"] == "**** **** 947"
    account_id=created.json()["id"]
    assert api.patch(f"/api/farms/farm-b/bank-accounts/{account_id}",cookies=cookies(),headers=headers(),json={"display_name":"Angrep"}).status_code == 404
    assert api.delete(f"/api/farms/farm-a/bank-accounts/{account_id}",cookies=cookies(),headers=headers()).status_code == 204
    assert state.accounts.items[account_id]["status"] == "inactive"
    manager,_=make_client(monkeypatch,"manager")
    assert manager.get("/api/farms/farm-a/bank-accounts",cookies=cookies()).status_code == 403
