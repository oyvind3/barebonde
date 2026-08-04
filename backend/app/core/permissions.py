"""Static Farm role permissions for the membership MVP."""

from __future__ import annotations

from enum import Enum


class Permission(str, Enum):
    FARM_SETTINGS_READ = "farm.settings.read"
    FARM_SETTINGS_UPDATE = "farm.settings.update"
    BANK_ACCOUNT_READ = "bank_account.read"
    BANK_ACCOUNT_CREATE = "bank_account.create"
    BANK_ACCOUNT_UPDATE = "bank_account.update"
    BANK_ACCOUNT_DELETE = "bank_account.delete"
    FARM_READ = "farm.read"
    FARM_UPDATE = "farm.update"
    FARM_ARCHIVE = "farm.archive"
    MEMBER_LIST = "member.list"
    MEMBER_INVITATION_LIST = "member.invitation.list"
    MEMBER_INVITE = "member.invite"
    MEMBER_INVITATION_RESEND = "member.invitation.resend"
    MEMBER_INVITATION_REVOKE = "member.invitation.revoke"
    MEMBER_ROLE_UPDATE = "member.role.update"
    MEMBER_STATUS_UPDATE = "member.status.update"
    MEMBER_REMOVE = "member.remove"
    OWNERSHIP_TRANSFER = "ownership.transfer"
    SUBSCRIPTION_READ = "subscription.read"
    SUBSCRIPTION_MANAGE = "subscription.manage"
    VOUCHER_READ = "voucher.read"
    VOUCHER_CREATE = "voucher.create"
    VOUCHER_UPDATE = "voucher.update"
    VOUCHER_DELETE = "voucher.delete"
    VOUCHER_BOOK = "voucher.book"
    DOCUMENT_READ = "document.read"
    DOCUMENT_UPLOAD = "document.upload"
    DOCUMENT_DELETE = "document.delete"
    DOCUMENT_DOWNLOAD = "document.download"
    TRANSACTION_READ = "transaction.read"
    TRANSACTION_CREATE = "transaction.create"
    TRANSACTION_UPDATE = "transaction.update"
    TRANSACTION_DELETE = "transaction.delete"
    REPORT_BASIC_READ = "report.basic.read"
    REPORT_ADVANCED_READ = "report.advanced.read"


ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "owner": frozenset(Permission),
    "manager": frozenset(
        {
            Permission.FARM_SETTINGS_READ,
            Permission.FARM_SETTINGS_UPDATE,
            Permission.FARM_READ,
            Permission.FARM_UPDATE,
            Permission.MEMBER_LIST,
            Permission.SUBSCRIPTION_READ,
            Permission.VOUCHER_READ,
            Permission.VOUCHER_CREATE,
            Permission.VOUCHER_UPDATE,
            Permission.VOUCHER_BOOK,
            Permission.DOCUMENT_READ,
            Permission.DOCUMENT_UPLOAD,
            Permission.DOCUMENT_DOWNLOAD,
            Permission.TRANSACTION_READ,
            Permission.TRANSACTION_CREATE,
            Permission.TRANSACTION_UPDATE,
            Permission.REPORT_BASIC_READ,
            Permission.REPORT_ADVANCED_READ,
        }
    ),
    "staff": frozenset(
        {
            Permission.FARM_READ,
            Permission.VOUCHER_READ,
            Permission.VOUCHER_CREATE,
            Permission.DOCUMENT_READ,
            Permission.DOCUMENT_UPLOAD,
            Permission.DOCUMENT_DOWNLOAD,
            Permission.REPORT_BASIC_READ,
        }
    ),
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
