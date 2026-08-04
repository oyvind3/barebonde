import os

import pytest
from azure.cosmos import exceptions

os.environ.setdefault("COSMOS_DB_CONNECTION_STRING", "not-used-in-unit-tests")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("IDENTITY_HMAC_KEY", "test-identity-hmac-key")

from app.services.membership_service import MembershipService, MembershipUpdateError


class MembershipContainer:
    def __init__(self, items): self.items = {item["id"]: dict(item) for item in items}
    def read_item(self, *, item, partition_key):
        value = self.items.get(item)
        if not value or value["farm_id"] != partition_key: raise exceptions.CosmosResourceNotFoundError(message="missing", response=None)
        return dict(value)
    def query_items(self, *, parameters, **_):
        values = {p["name"]: p["value"] for p in parameters}
        return [dict(item) for item in self.items.values() if item["farm_id"] == values.get("@farm_id") and item["user_id"] == values.get("@user_id")]
    def replace_item(self, *, item, body, **_): self.items[item] = dict(body); return body


def member(user_id, role="staff", status="active"):
    return {"id": f"membership:farm-a:{user_id}", "farm_id": "farm-a", "user_id": user_id, "farm_role": role, "role": role, "membership_status": status, "version": 1}


def service(*members): return MembershipService(farm_users_container=MembershipContainer(members), farms_container=object())


def test_owner_cannot_be_changed_suspended_or_removed():
    target = service(member("owner", "owner"))
    for operation in (
        lambda: target.update_member_role(farm_id="farm-a", user_id="owner", actor_user_id="actor", role="staff"),
        lambda: target.update_member_status(farm_id="farm-a", user_id="owner", actor_user_id="actor", membership_status="suspended"),
        lambda: target.remove_member(farm_id="farm-a", user_id="owner", actor_user_id="actor"),
    ):
        with pytest.raises(MembershipUpdateError, match="cannot_modify_owner"): operation()


def test_role_status_and_soft_removal_preserve_role_history():
    target = service(member("staff"))
    assert target.update_member_role(farm_id="farm-a", user_id="staff", actor_user_id="owner", role="manager")["farm_role"] == "manager"
    assert target.update_member_status(farm_id="farm-a", user_id="staff", actor_user_id="owner", membership_status="suspended")["membership_status"] == "suspended"
    assert target.update_member_status(farm_id="farm-a", user_id="staff", actor_user_id="owner", membership_status="active")["membership_status"] == "active"
    removed = target.remove_member(farm_id="farm-a", user_id="staff", actor_user_id="owner")
    assert removed["membership_status"] == "removed" and removed["previous_farm_role"] == "manager"


def test_member_cannot_administer_itself_or_become_owner():
    target = service(member("staff"))
    with pytest.raises(MembershipUpdateError, match="cannot_modify_self"):
        target.update_member_role(farm_id="farm-a", user_id="staff", actor_user_id="staff", role="manager")
    with pytest.raises(MembershipUpdateError, match="invalid_member_role"):
        target.update_member_role(farm_id="farm-a", user_id="staff", actor_user_id="owner", role="owner")
