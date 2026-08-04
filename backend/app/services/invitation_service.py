"""Farm-scoped, opaque-token invitations. Invitations never grant access alone."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from azure.cosmos import exceptions

from app.core.security_tokens import hmac_identifier, new_opaque_token
from app.db.cosmos_client import get_farm_invitations_container
from app.services.identity_service import IdentityService, normalize_email
from app.services.membership_service import MembershipService, membership_id, utc_now


class InvitationError(Exception):
    pass


class InvitationConflictError(InvitationError):
    pass


class InvitationService:
    """Keep invitation records separate from FarmUser until explicit acceptance."""

    ttl_seconds = 7 * 24 * 60 * 60

    def __init__(self, *, invitations_container: Any | None = None, membership_service: MembershipService | None = None, identity_service: IdentityService | None = None):
        self.invitations = invitations_container or get_farm_invitations_container()
        self.memberships = membership_service or MembershipService()
        self.identities = identity_service or IdentityService()

    @staticmethod
    def invitation_id(farm_id: str, email: str) -> str:
        return f"farm-invitation:{hmac_identifier('farm-invitation', f'{farm_id}:{normalize_email(email)}')}"

    @staticmethod
    def token_hash(secret: str) -> str:
        return hmac_identifier("farm-invitation-token", secret)

    def create_invitation(self, *, farm: dict[str, Any], email: str, role: str, actor_user_id: str) -> tuple[dict[str, Any], str]:
        if role not in {"manager", "staff"}:
            raise InvitationError("invalid_member_role")
        normalized = normalize_email(email)
        farm_id = str(farm["id"])
        existing_member = self.memberships.get_membership(farm_id=farm_id, user_id=(self.identities.find_existing_email_identity(normalized) or {}).get("user_id", ""))
        if existing_member is not None:
            raise InvitationConflictError("member_already_exists")
        invitation_id = self.invitation_id(farm_id, normalized)
        try:
            current = self.invitations.read_item(item=invitation_id, partition_key=farm_id)
            if current.get("invitation_status") == "pending":
                raise InvitationConflictError("invitation_already_pending")
        except exceptions.CosmosResourceNotFoundError:
            pass
        secret = new_opaque_token()
        now = datetime.now(timezone.utc)
        target = self.identities.find_existing_email_identity(normalized)
        document = {
            "id": invitation_id, "type": "farm_invitation", "farm_id": farm_id,
            "email": normalized, "email_normalized": normalized,
            "email_lookup_hash": hmac_identifier("farm-invitation-email", normalized),
            "invited_role": role, "invitation_status": "pending", "invited_by_user_id": actor_user_id,
            "target_user_id": target.get("user_id") if target else None,
            "token_hash": self.token_hash(secret), "token_key_version": 1,
            "created_at": utc_now(), "updated_at": utc_now(),
            "expires_at": (now + timedelta(seconds=self.ttl_seconds)).isoformat(),
            "accepted_at": None, "accepted_by_user_id": None, "revoked_at": None, "revoked_by_user_id": None,
            "send_count": 1, "last_sent_at": None, "failed_attempts": 0, "ttl": self.ttl_seconds, "version": 1,
        }
        try:
            self.invitations.create_item(document)
        except exceptions.CosmosResourceExistsError as exc:
            raise InvitationConflictError("invitation_already_pending") from exc
        return document, secret

    def list_invitations(self, farm_id: str) -> list[dict[str, Any]]:
        return list(self.invitations.query_items(query="SELECT * FROM c WHERE c.farm_id = @farm_id", parameters=[{"name": "@farm_id", "value": farm_id}], partition_key=farm_id))

    def public_metadata(self, invitation: dict[str, Any]) -> dict[str, Any]:
        return {key: invitation.get(key) for key in ("id", "email", "invited_role", "invitation_status", "invited_by_user_id", "created_at", "expires_at", "last_sent_at", "send_count")}

