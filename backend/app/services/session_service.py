"""Server-managed opaque browser sessions stored in Cosmos."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from azure.cosmos import exceptions

from app.core.config import settings
from app.core.security_tokens import csrf_token_for_session, new_opaque_token, session_identifier
from app.db.cosmos_client import get_auth_sessions_container
from app.services.identity_service import IdentityError, IdentityService, utc_now


class InvalidSessionError(IdentityError):
    """A cookie does not resolve to a live session."""


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class SessionService:
    def __init__(self, *, sessions_container: Any | None = None, identity_service: IdentityService | None = None):
        self.sessions = sessions_container or get_auth_sessions_container()
        self.identity = identity_service or IdentityService()

    def create_session(self, user: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        user = self.identity._require_active(user)
        raw_token = new_opaque_token()
        session_id = session_identifier(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.identity_session_ttl_seconds)
        session = {
            "id": session_id,
            "type": "auth_session",
            "session_partition_id": session_id,
            "user_id": user["user_id"],
            "user_partition_key": self.identity.user_partition_key(user),
            "created_at": utc_now(),
            "last_seen_at": utc_now(),
            "expires_at": expires_at.isoformat(),
            "revoked_at": None,
        }
        self.sessions.create_item(session)
        return raw_token, session

    def get_session(self, raw_token: str) -> tuple[dict[str, Any], dict[str, Any]]:
        session_id = session_identifier(raw_token)
        try:
            session = self.sessions.read_item(item=session_id, partition_key=session_id)
        except exceptions.CosmosResourceNotFoundError as exc:
            raise InvalidSessionError("Sesjonen finnes ikke eller er utløpt.") from exc
        expires_at = _parse_time(session.get("expires_at"))
        if session.get("revoked_at") or not expires_at or expires_at <= datetime.now(timezone.utc):
            raise InvalidSessionError("Sesjonen er utløpt eller tilbakekalt.")
        user = self.identity.get_user(str(session.get("user_id") or ""), str(session.get("user_partition_key") or ""))
        return session, user

    def csrf_token(self, raw_token: str) -> str:
        return csrf_token_for_session(raw_token)

    def list_sessions(self, user: dict[str, Any], current_raw_token: str) -> list[dict[str, Any]]:
        current_id = session_identifier(current_raw_token)
        sessions = list(
            self.sessions.query_items(
                query="SELECT * FROM c WHERE c.user_id = @user_id",
                parameters=[{"name": "@user_id", "value": user["user_id"]}],
                enable_cross_partition_query=True,
            )
        )
        return [
            {
                "session_id": session["id"],
                "created_at": session.get("created_at"),
                "last_seen_at": session.get("last_seen_at"),
                "expires_at": session.get("expires_at"),
                "current": session["id"] == current_id,
            }
            for session in sessions
            if not session.get("revoked_at")
            and (_parse_time(session.get("expires_at")) or datetime.min.replace(tzinfo=timezone.utc))
            > datetime.now(timezone.utc)
        ]

    def revoke_session(self, *, user: dict[str, Any], session_id: str) -> bool:
        try:
            session = self.sessions.read_item(item=session_id, partition_key=session_id)
        except exceptions.CosmosResourceNotFoundError:
            return False
        if session.get("user_id") != user.get("user_id"):
            raise InvalidSessionError("Sesjonen tilhører ikke brukeren.")
        if not session.get("revoked_at"):
            session["revoked_at"] = utc_now()
            self.sessions.upsert_item(session)
        return True

    def revoke_other_sessions(self, *, user: dict[str, Any], keep_session_id: str) -> int:
        """Revoke all sessions for a user except the specified one.
        
        Returns the count of revoked sessions.
        """
        current_id = session_identifier(keep_session_id) if len(keep_session_id) > 32 else keep_session_id
        sessions = list(
            self.sessions.query_items(
                query="SELECT * FROM c WHERE c.user_id = @user_id",
                parameters=[{"name": "@user_id", "value": user["user_id"]}],
                enable_cross_partition_query=True,
            )
        )
        revoked_count = 0
        for session in sessions:
            if session["id"] != current_id and not session.get("revoked_at"):
                session["revoked_at"] = utc_now()
                self.sessions.upsert_item(session)
                revoked_count += 1
        return revoked_count
