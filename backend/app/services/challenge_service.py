"""One-time e-mail login challenges backed by Cosmos."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from azure.core import MatchConditions
from azure.cosmos import exceptions

from app.core.config import settings
from app.core.security_tokens import challenge_identifier, new_opaque_token
from app.db.cosmos_client import get_auth_challenges_container
from app.services.identity_service import IdentityError, IdentityService, utc_now


class InvalidChallengeError(IdentityError):
    """The magic-link token is missing, expired, revoked, or already used."""


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class ChallengeService:
    def __init__(self, *, challenges_container: Any | None = None, identity_service: IdentityService | None = None):
        self.challenges = challenges_container or get_auth_challenges_container()
        self.identity = identity_service or IdentityService()

    def create_email_login_challenge(self, *, email: str, first_name: str = "Bonde") -> str:
        user = self.identity.find_existing_email_identity(email)
        if user is None:
            raise IdentityError("account_not_found")
        return self._create_challenge(challenge_type="email_login", user=user)

    def _create_challenge(
        self,
        *,
        challenge_type: str,
        user: dict[str, Any] | None = None,
        email: str | None = None,
        registration_profile: dict[str, Any] | None = None,
    ) -> str:
        raw_token = new_opaque_token()
        challenge_id = challenge_identifier(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.identity_magic_link_ttl_seconds)
        self.challenges.create_item(
            {
                "id": challenge_id,
                "type": "auth_challenge",
                "challenge_partition_id": challenge_id,
                "challenge_type": challenge_type,
                "user_id": user["user_id"] if user else None,
                "user_partition_key": self.identity.user_partition_key(user) if user else None,
                "registration_email": email,
                "registration_profile": registration_profile,
                "created_at": utc_now(),
                "expires_at": expires_at.isoformat(),
                "consumed_at": None,
            }
        )
        return raw_token

    def create_email_registration_challenge(
        self, *, email: str, registration_profile: dict[str, Any] | None = None
    ) -> str:
        normalized = email.strip().casefold()
        if self.identity.find_existing_email_identity(normalized) is not None:
            raise IdentityError("account_already_exists")
        return self._create_challenge(
            challenge_type="email_registration",
            email=normalized,
            registration_profile=registration_profile,
        )

    def consume_email_login_challenge(self, raw_token: str) -> dict[str, Any]:
        return self.consume_email_challenge(raw_token, expected_type="email_login")

    def consume_email_challenge(self, raw_token: str, *, expected_type: str | None = None) -> dict[str, Any]:
        challenge_id = challenge_identifier(raw_token)
        try:
            challenge = self.challenges.read_item(item=challenge_id, partition_key=challenge_id)
        except exceptions.CosmosResourceNotFoundError as exc:
            raise InvalidChallengeError("Innloggingslenken er ugyldig eller er allerede brukt.") from exc

        expires_at = _parse_time(challenge.get("expires_at"))
        now = datetime.now(timezone.utc)
        if (expected_type and challenge.get("challenge_type") != expected_type) or challenge.get("challenge_type") not in {"email_login", "email_registration"} or challenge.get("consumed_at") or not expires_at or expires_at <= now:
            raise InvalidChallengeError("Innloggingslenken er utløpt eller allerede brukt.")

        challenge["consumed_at"] = utc_now()
        try:
            self.challenges.replace_item(
                item=challenge_id,
                body=challenge,
                etag=challenge.get("_etag"),
                match_condition=MatchConditions.IfNotModified if challenge.get("_etag") else None,
            )
        except (exceptions.CosmosHttpResponseError, exceptions.CosmosResourceNotFoundError) as exc:
            raise InvalidChallengeError("Innloggingslenken er allerede brukt.") from exc
        if challenge.get("challenge_type") == "email_registration":
            profile = challenge.get("registration_profile") or {}
            user = self.identity.resolve_email_identity(
                email=str(challenge.get("registration_email") or ""),
                first_name=str(profile.get("first_name") or "Bonde"),
            )
            allowed_profile_fields = {"first_name", "last_name", "phone_number", "address", "onboarding_role"}
            profile_updates = {key: value for key, value in profile.items() if key in allowed_profile_fields and value is not None}
            
            # Handle password if provided during registration
            password = profile.get("password")
            if password:
                from app.services.password_service import PasswordService
                password_hash = PasswordService.hash_password(password)
                profile_updates["password_hash"] = password_hash
                profile_updates["password_set_at"] = utc_now()
            
            if profile_updates:
                user = self.identity.update_profile(user, profile_updates)
        else:
            user = self.identity.get_user(challenge["user_id"], challenge["user_partition_key"])

        # Completing a one-time e-mail challenge is the verification event for
        # both login and registration.  Persist it before starting a session.
        return self.identity.update_profile(user, {"email_verified": True})
