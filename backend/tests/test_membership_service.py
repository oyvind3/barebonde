import os

import pytest
from azure.cosmos import exceptions

os.environ.setdefault("COSMOS_DB_CONNECTION_STRING", "not-used-in-unit-tests")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("IDENTITY_HMAC_KEY", "test-identity-hmac-key")

from app.core.permissions import Permission, ROLE_PERMISSIONS, permissions_for_role
from app.db.cosmos_models import FarmUser
from app.services.membership_service import (
    InactiveMembershipError,
    MembershipService,
    membership_id,
)


class MemoryContainer:
    def __init__(self):
        self.items = {}

    def create_item(self, item):
        if item["id"] in self.items:
            raise exceptions.CosmosResourceExistsError(message="exists", response=None)
        self.items[item["id"]] = dict(item)

    def upsert_item(self, item):
        self.items[item["id"]] = dict(item)

    def read_item(self, item, partition_key):
        document = self.items.get(item)
        if document is None or document.get("farm_id") != partition_key:
            raise exceptions.CosmosResourceNotFoundError(message="missing", response=None)
        return dict(document)

    def query_items(self, *, query, parameters, **_):
        values = {item["name"]: item["value"] for item in parameters}
        if "c.user_id" in query:
            return [item for item in self.items.values() if item.get("user_id") == values["@user_id"] and (
                "@farm_id" not in values or item.get("farm_id") == values["@farm_id"]
            )]
        if "c.farm_id" in query:
            return [item for item in self.items.values() if item.get("farm_id") == values["@farm_id"]]
        if "c.org_number" in query:
            return [item for item in self.items.values() if item.get("org_number") == values["@org_number"]]
        if "c.id" in query:
            return [item for item in self.items.values() if item.get("id") == values["@farm_id"]]
        return []


def service():
    return MembershipService(farm_users_container=MemoryContainer(), farms_container=MemoryContainer())


def test_role_permissions_are_static_distinct_and_unknown_roles_have_none():
    assert Permission.FARM_ARCHIVE in permissions_for_role("owner")
    assert Permission.FARM_UPDATE in permissions_for_role("manager")
    assert Permission.VOUCHER_BOOK in permissions_for_role("manager")
    assert Permission.VOUCHER_CREATE in permissions_for_role("staff")
    assert Permission.DOCUMENT_DOWNLOAD in permissions_for_role("staff")
    assert Permission.VOUCHER_BOOK not in permissions_for_role("staff")
    assert permissions_for_role("unknown") == frozenset()
    assert all(len(values) == len(set(values)) for values in ROLE_PERMISSIONS.values())


def test_membership_id_is_deterministic_and_owner_creation_is_idempotent():
    membership_service = service()
    farm = {"id": "farm:123456789", "name": "Solberg gård", "org_number": "123456789"}

    first = membership_service.create_owner_membership(farm=farm, user_id="user-1")
    second = membership_service.create_owner_membership(farm=farm, user_id="user-1")

    assert membership_id("farm:123456789", "user-1") == "membership:farm:123456789:user-1"
    assert first["id"] == second["id"] == "membership:farm:123456789:user-1"
    assert first["farm_role"] == first["role"] == "owner"
    assert first["membership_status"] == "active"
    assert len(membership_service.farm_users.items) == 1


def test_legacy_role_and_missing_status_remain_active_but_unknown_roles_do_not_grant_access():
    membership_service = service()
    membership_service.farm_users.items["legacy"] = {
        "id": "legacy",
        "farm_id": "farm-1",
        "user_id": "user-1",
        "role": "manager",
    }
    active = membership_service.get_active_membership(farm_id="farm-1", user_id="user-1")

    assert active["farm_role"] == "manager"
    assert active["membership_status"] == "active"
    assert Permission.FARM_UPDATE in membership_service.permissions_for_membership(active)

    membership_service.farm_users.items["legacy"]["role"] = "untrusted-role"
    with pytest.raises(InactiveMembershipError):
        membership_service.get_active_membership(farm_id="farm-1", user_id="user-1")


def test_farm_user_model_prefers_farm_role_and_writes_legacy_role_for_compatibility():
    membership = FarmUser.from_dict(
        {
            "id": "legacy-id",
            "farm_id": "farm-1",
            "user_id": "user-1",
            "farm_role": "manager",
            "role": "staff",
        }
    )

    assert membership.farm_role == "manager"
    assert membership.to_dict()["role"] == "manager"


@pytest.mark.parametrize("membership_status", ["suspended", "removed"])
def test_non_active_memberships_do_not_authorize(membership_status):
    membership_service = service()
    membership_service.farm_users.items[membership_id("farm-1", "user-1")] = {
        "id": membership_id("farm-1", "user-1"),
        "farm_id": "farm-1",
        "user_id": "user-1",
        "farm_role": "owner",
        "membership_status": membership_status,
    }

    with pytest.raises(InactiveMembershipError):
        membership_service.get_active_membership(farm_id="farm-1", user_id="user-1")


def test_list_active_memberships_filters_suspended_and_removed_documents():
    membership_service = service()
    for farm_id, role, membership_status in (
        ("farm-a", "owner", "active"),
        ("farm-b", "manager", "suspended"),
        ("farm-c", "staff", "removed"),
    ):
        identifier = membership_id(farm_id, "user-1")
        membership_service.farm_users.items[identifier] = {
            "id": identifier,
            "farm_id": farm_id,
            "user_id": "user-1",
            "farm_role": role,
            "membership_status": membership_status,
        }

    assert [item["farm_id"] for item in membership_service.list_active_memberships_for_user("user-1")] == ["farm-a"]
