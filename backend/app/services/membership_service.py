"""Authoritative FarmUser membership and lightweight farm lookup helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from azure.cosmos import exceptions

from app.core.permissions import Permission, normalize_farm_role, permissions_for_role
from app.db.cosmos_client import get_farm_users_container, get_farms_container
from app.db.cosmos_models import FarmUser


class MembershipError(Exception):
    """Base class for expected membership failures."""


class MembershipNotFoundError(MembershipError):
    pass


class InactiveMembershipError(MembershipError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def membership_id(farm_id: str, user_id: str) -> str:
    """The sole format used for point-readable FarmUser documents."""
    return FarmUser.membership_id(farm_id, user_id)


class MembershipService:
    def __init__(self, *, farm_users_container: Any | None = None, farms_container: Any | None = None):
        self.farm_users = farm_users_container or get_farm_users_container()
        self.farms = farms_container or get_farms_container()

    @staticmethod
    def normalize_membership(document: dict[str, Any]) -> dict[str, Any]:
        """Read legacy ``role`` documents safely without mutating them blindly."""
        normalized = dict(document)
        normalized["farm_role"] = normalize_farm_role(
            document.get("farm_role") or document.get("role")
        )
        normalized["membership_status"] = str(document.get("membership_status") or "active").casefold()
        return normalized

    @staticmethod
    def is_active(document: dict[str, Any]) -> bool:
        return document.get("membership_status") == "active" and bool(document.get("farm_role"))

    def get_membership(self, *, farm_id: str, user_id: str) -> dict[str, Any] | None:
        identifier = membership_id(farm_id, user_id)
        try:
            document = self.farm_users.read_item(item=identifier, partition_key=farm_id)
        except exceptions.CosmosResourceNotFoundError:
            # Pre-membership documents used random IDs. Preserve access for an
            # existing valid legacy link without creating a new duplicate.
            documents = list(
                self.farm_users.query_items(
                    query="SELECT * FROM c WHERE c.farm_id = @farm_id AND c.user_id = @user_id",
                    parameters=[
                        {"name": "@farm_id", "value": farm_id},
                        {"name": "@user_id", "value": user_id},
                    ],
                    partition_key=farm_id,
                )
            )
            if len(documents) != 1:
                return None
            document = documents[0]
        return self.normalize_membership(document)

    def get_active_membership(self, *, farm_id: str, user_id: str) -> dict[str, Any]:
        membership = self.get_membership(farm_id=farm_id, user_id=user_id)
        if membership is None:
            raise MembershipNotFoundError("Farm-medlemskap mangler.")
        if not self.is_active(membership):
            raise InactiveMembershipError("Farm-medlemskapet er ikke aktivt.")
        return membership

    def permissions_for_membership(self, membership: dict[str, Any]) -> frozenset[Permission]:
        return permissions_for_role(membership.get("farm_role")) if self.is_active(membership) else frozenset()

    def create_owner_membership(self, *, farm: dict[str, Any], user_id: str) -> dict[str, Any]:
        """Create a single owner membership, or return an existing active one."""
        farm_id = str(farm["id"])
        existing = self.get_membership(farm_id=farm_id, user_id=user_id)
        if existing is not None:
            if self.is_active(existing):
                return existing
            raise InactiveMembershipError("Et inaktivt medlemskap kan ikke overtas automatisk.")

        timestamp = utc_now()
        document = {
            "id": membership_id(farm_id, user_id),
            "type": "farm_user",
            "farm_id": farm_id,
            "user_id": user_id,
            "farm_role": "owner",
            "role": "owner",
            "membership_status": "active",
            "invited_by_user_id": None,
            "invited_at": None,
            "accepted_at": timestamp,
            "expires_at": None,
            "created_at": timestamp,
            "updated_at": timestamp,
            "version": 1,
            "farm_name": str(farm.get("name") or ""),
            "org_number": str(farm.get("org_number") or ""),
        }
        try:
            self.farm_users.create_item(document)
            return self.normalize_membership(document)
        except exceptions.CosmosResourceExistsError:
            existing = self.get_membership(farm_id=farm_id, user_id=user_id)
            if existing and self.is_active(existing):
                return existing
            raise MembershipError("Medlemskapet kunne ikke opprettes trygt.")

    def list_active_memberships_for_user(self, user_id: str) -> list[dict[str, Any]]:
        documents = list(
            self.farm_users.query_items(
                query="SELECT * FROM c WHERE c.user_id = @user_id",
                parameters=[{"name": "@user_id", "value": user_id}],
                enable_cross_partition_query=True,
            )
        )
        return [
            membership
            for document in documents
            if self.is_active(membership := self.normalize_membership(document))
        ]

    def list_members_for_farm(self, farm_id: str) -> list[dict[str, Any]]:
        documents = list(
            self.farm_users.query_items(
                query="SELECT * FROM c WHERE c.farm_id = @farm_id",
                parameters=[{"name": "@farm_id", "value": farm_id}],
                partition_key=farm_id,
            )
        )
        return [self.normalize_membership(document) for document in documents]

    def get_farm(self, farm_id: str) -> dict[str, Any] | None:
        farms = list(
            self.farms.query_items(
                query="SELECT * FROM c WHERE c.id = @farm_id",
                parameters=[{"name": "@farm_id", "value": farm_id}],
                enable_cross_partition_query=True,
            )
        )
        return farms[0] if len(farms) == 1 else None

    def get_farm_by_org_number(self, org_number: str) -> dict[str, Any] | None:
        farms = list(
            self.farms.query_items(
                query="SELECT * FROM c WHERE c.org_number = @org_number",
                parameters=[{"name": "@org_number", "value": org_number}],
                enable_cross_partition_query=True,
            )
        )
        return farms[0] if len(farms) == 1 else None
