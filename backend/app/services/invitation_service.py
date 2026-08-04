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

    def get_invitation(self, *, farm_id: str, invitation_id: str) -> dict[str, Any]:
        try:
            return self.invitations.read_item(item=invitation_id, partition_key=farm_id)
        except exceptions.CosmosResourceNotFoundError as exc:
            raise InvitationError("invitation_not_found") from exc

    def verify_token(self, raw_token: str) -> tuple[dict[str, Any], str]:
        """Validate without consuming. GET callers get only an opaque completion intent."""
        parts = raw_token.split(".")
        if len(parts) != 4 or parts[0] != "v1" or len(raw_token) > 800:
            raise InvitationError("invitation_not_found")
        farm_id, invitation_id, secret = parts[1:]
        invitation = self.get_invitation(farm_id=farm_id, invitation_id=invitation_id)
        expires = datetime.fromisoformat(str(invitation["expires_at"]).replace("Z", "+00:00"))
        if invitation.get("invitation_status") != "pending" or expires <= datetime.now(timezone.utc):
            raise InvitationError("invitation_expired")
        if self.token_hash(secret) != invitation.get("token_hash"):
            raise InvitationError("invitation_not_found")
        intent_signature = hmac_identifier("farm-invitation-intent", f"{invitation_id}:{invitation['token_hash']}")
        return invitation, f"v1.{invitation_id}.{intent_signature}"

    def accept(self, *, intent: str, user: dict[str, Any]) -> dict[str, Any]:
        parts = intent.split(".")
        if len(parts) != 3 or parts[0] != "v1":
            raise InvitationError("invitation_not_found")
        invitation_id = parts[1]
        # An ID is opaque, but resolve its Farm only after a constrained query.
        matches = list(self.invitations.query_items(query="SELECT * FROM c WHERE c.id = @id", parameters=[{"name": "@id", "value": invitation_id}], enable_cross_partition_query=True))
        if len(matches) != 1:
            raise InvitationError("invitation_not_found")
        invitation = matches[0]
        expected = hmac_identifier("farm-invitation-intent", f"{invitation_id}:{invitation['token_hash']}")
        if parts[2] != expected:
            raise InvitationError("invitation_not_found")
        if normalize_email(str(user.get("email") or "")) != invitation["email_normalized"] or not user.get("email_verified"):
            raise InvitationError("invitation_email_mismatch")
        if invitation.get("invitation_status") == "accepted":
            existing = self.memberships.get_membership(farm_id=invitation["farm_id"], user_id=user["user_id"])
            if existing and self.memberships.is_active(existing):
                return existing
            raise InvitationConflictError("invitation_already_accepted")
        if invitation.get("invitation_status") != "pending":
            raise InvitationError("invitation_not_found")
        now = utc_now(); farm_id = invitation["farm_id"]
        membership = {"id": membership_id(farm_id, user["user_id"]), "type": "farm_user", "farm_id": farm_id, "user_id": user["user_id"], "farm_role": invitation["invited_role"], "role": invitation["invited_role"], "membership_status": "active", "invited_by_user_id": invitation["invited_by_user_id"], "invited_at": invitation["created_at"], "accepted_at": now, "created_at": now, "updated_at": now, "version": 1}
        try:
            self.memberships.farm_users.create_item(membership)
        except exceptions.CosmosResourceExistsError:
            existing = self.memberships.get_membership(farm_id=farm_id, user_id=user["user_id"])
            if not existing or existing.get("farm_role") != invitation["invited_role"]:
                raise InvitationConflictError("member_already_exists")
            membership = existing
        invitation.update({"invitation_status": "accepted", "accepted_at": now, "accepted_by_user_id": user["user_id"], "updated_at": now})
        self.invitations.upsert_item(invitation)
        return membership
