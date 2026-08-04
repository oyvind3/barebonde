"""Static Farm role permissions for the membership MVP."""

from __future__ import annotations

from enum import Enum


class Permission(str, Enum):
    FARM_READ = "farm.read"
    FARM_UPDATE = "farm.update"
    FARM_ARCHIVE = "farm.archive"
    MEMBER_LIST = "member.list"
    SUBSCRIPTION_READ = "subscription.read"
    SUBSCRIPTION_MANAGE = "subscription.manage"


ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "owner": frozenset(Permission),
    "manager": frozenset(
        {
            Permission.FARM_READ,
            Permission.FARM_UPDATE,
            Permission.MEMBER_LIST,
            Permission.SUBSCRIPTION_READ,
        }
    ),
    "staff": frozenset({Permission.FARM_READ}),
}


def normalize_farm_role(role: object) -> str | None:
    normalized = str(role or "").strip().casefold()
    return normalized if normalized in ROLE_PERMISSIONS else None


def permissions_for_role(role: object) -> frozenset[Permission]:
    """Return no permissions for an unknown role rather than guessing."""
    normalized = normalize_farm_role(role)
    return ROLE_PERMISSIONS.get(normalized or "", frozenset())


def role_has_permission(role: object, permission: Permission) -> bool:
    return permission in permissions_for_role(role)
