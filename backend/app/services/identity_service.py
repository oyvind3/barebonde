"""Identity persistence built directly on the existing Cosmos containers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from azure.cosmos import exceptions

from app.core.security_tokens import email_lookup_identifier, google_lookup_identifier
from app.db.cosmos_client import get_identity_lookups_container, get_users_container
from app.db.cosmos_models import User


class IdentityError(Exception):
    """Base class for expected Identity errors."""


class IdentityConflictError(IdentityError):
    """Two credentials resolve to different internal users."""


class DisabledUserError(IdentityError):
    """An inactive user attempted to authenticate."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def _is_not_found(exc: Exception) -> bool:
    return isinstance(exc, (exceptions.CosmosResourceNotFoundError, KeyError))


class IdentityService:
    """Resolve external identities to stable Barebonde user documents.

    ``users`` retains its legacy ``/better_auth_id`` partition key. The new
    lookup container is only an opaque index and deliberately holds neither
    e-mail addresses nor Google subjects.
    """

    def __init__(self, *, users_container: Any | None = None, lookups_container: Any | None = None):
        self.users = users_container or get_users_container()
        self.lookups = lookups_container or get_identity_lookups_container()

    @staticmethod
    def user_partition_key(user: dict[str, Any]) -> str:
        partition_key = str(user.get("better_auth_id") or "")
        if not partition_key:
            raise IdentityError("Brukerdokumentet mangler partisjonsnøkkel.")
        return partition_key

    def _read_lookup(self, lookup_id: str) -> dict[str, Any] | None:
        try:
            return self.lookups.read_item(item=lookup_id, partition_key=lookup_id)
        except Exception as exc:
            if _is_not_found(exc):
                return None
            raise

    def _read_user(self, user_id: str, partition_key: str) -> dict[str, Any] | None:
        try:
            return self.users.read_item(item=user_id, partition_key=partition_key)
        except Exception as exc:
            if _is_not_found(exc):
                return None
            raise

    def _upgrade_user_document(self, user: dict[str, Any]) -> dict[str, Any]:
        """Add the new fields to legacy documents without changing their PK."""
        changed = False
        user_id = str(user.get("user_id") or user.get("id") or "")
        if not user_id:
            raise IdentityError("Brukerdokumentet mangler intern ID.")
        if user.get("user_id") != user_id:
            user["user_id"] = user_id
            changed = True
        normalized = normalize_email(str(user.get("email") or ""))
        if not normalized:
            raise IdentityError("Brukerdokumentet mangler e-postadresse.")
        if user.get("email_normalized") != normalized:
            user["email_normalized"] = normalized
            changed = True
        status = user.get("status") or ("active" if user.get("is_active", True) else "disabled")
        if user.get("status") != status:
            user["status"] = status
            changed = True
        if "identity_version" not in user:
            user["identity_version"] = 1
            changed = True
        if "updated_at" not in user:
            user["updated_at"] = user.get("created_at") or utc_now()
            changed = True
        self.user_partition_key(user)
        if changed:
            user["updated_at"] = utc_now()
            self.users.upsert_item(user)
        return user

    def _require_active(self, user: dict[str, Any]) -> dict[str, Any]:
        user = self._upgrade_user_document(user)
        if user.get("status") != "active" or user.get("is_active") is False:
            raise DisabledUserError("Brukerkontoen er deaktivert.")
        return user

    def get_user(self, user_id: str, partition_key: str) -> dict[str, Any]:
        user = self._read_user(user_id, partition_key)
        if user is None:
            raise IdentityError("Brukeren finnes ikke lenger.")
        return self._require_active(user)

    def _lookup_user(self, lookup_id: str) -> dict[str, Any] | None:
        lookup = self._read_lookup(lookup_id)
        if lookup is None:
            return None
        user = self._read_user(str(lookup.get("user_id") or ""), str(lookup.get("user_partition_key") or ""))
        if user is None:
            raise IdentityError("Identity-oppslaget peker på en bruker som ikke finnes.")
        return self._require_active(user)

    def _ensure_lookup(self, *, lookup_id: str, lookup_type: str, user: dict[str, Any]) -> None:
        existing = self._read_lookup(lookup_id)
        user_id = str(user["user_id"])
        partition_key = self.user_partition_key(user)
        if existing:
            if existing.get("user_id") != user_id or existing.get("user_partition_key") != partition_key:
                raise IdentityConflictError("Identiteten er allerede koblet til en annen bruker.")
            return

        document = {
            "id": lookup_id,
            "type": "identity_lookup",
            "lookup_partition_id": lookup_id,
            "lookup_type": lookup_type,
            "user_id": user_id,
            "user_partition_key": partition_key,
            "created_at": utc_now(),
        }
        try:
            self.lookups.create_item(document)
        except exceptions.CosmosResourceExistsError:
            # A parallel registration won the deterministic lookup key. Re-read
            # it so the collision cannot silently attach two users.
            existing = self._read_lookup(lookup_id)
            if not existing or existing.get("user_id") != user_id:
                raise IdentityConflictError("Identiteten ble registrert samtidig av en annen bruker.")

    def _find_legacy_user(self, *, field: str, value: str) -> dict[str, Any] | None:
        """Migration fallback for profiles created before identity_lookups existed."""
        users = list(
            self.users.query_items(
                query=f"SELECT * FROM c WHERE c.{field} = @value",
                parameters=[{"name": "@value", "value": value}],
                enable_cross_partition_query=True,
            )
        )
        if len(users) > 1:
            raise IdentityConflictError("Flere eksisterende brukerprofiler har samme identitet.")
        return self._require_active(users[0]) if users else None

    def _find_by_email(self, normalized_email: str) -> dict[str, Any] | None:
        user = self._lookup_user(email_lookup_identifier(normalized_email))
        if user is not None:
            return user
        user = self._find_legacy_user(field="email_normalized", value=normalized_email)
        if user is None:
            user = self._find_legacy_user(field="email", value=normalized_email)
        if user is not None:
            self._ensure_lookup(
                lookup_id=email_lookup_identifier(normalized_email), lookup_type="email", user=user
            )
        return user

    def _new_user(self, *, email: str, first_name: str = "Bonde", last_name: str = "", google_id: str | None = None,
                  picture: str | None = None) -> dict[str, Any]:
        user_id = str(uuid4())
        user = User(
            id=user_id,
            user_id=user_id,
            email=normalize_email(email),
            better_auth_id=f"user_{user_id}",
            first_name=first_name.strip() or "Bonde",
            last_name=last_name.strip(),
            google_id=google_id,
            status="active",
            identity_version=1,
        ).to_dict()
        if picture:
            user["picture"] = picture
        self.users.create_item(user)
        return user

    @staticmethod
    def _google_email_can_link_existing_account(email: str, hosted_domain: str | None) -> bool:
        """Only auto-link an existing account when Google is authoritative for e-mail."""
        return email.endswith("@gmail.com") or bool(hosted_domain)

    def resolve_google_identity(
        self,
        *,
        google_id: str,
        email: str,
        first_name: str,
        last_name: str = "",
        picture: str | None = None,
        hosted_domain: str | None = None,
    ) -> dict[str, Any]:
        normalized_email = normalize_email(email)
        google_lookup_id = google_lookup_identifier(google_id)
        user = self._lookup_user(google_lookup_id)
        if user is None:
            legacy_google = self._find_legacy_user(field="google_id", value=google_id)
            if legacy_google is not None:
                user = legacy_google
                self._ensure_lookup(lookup_id=google_lookup_id, lookup_type="google_subject", user=user)

        # Google ``sub`` is the stable provider identifier. Once it is linked,
        # a later Google e-mail-address change must not block the user or make
        # us compare it with an unrelated legacy e-mail profile.
        if user:
            return user

        email_user = self._find_by_email(normalized_email)

        if email_user is not None:
            if not self._google_email_can_link_existing_account(normalized_email, hosted_domain):
                raise IdentityConflictError(
                    "Google kan ikke automatisk koble denne eksterne e-postadressen. Logg inn med e-postlenke først."
                )
            user = email_user
            if not user.get("google_id"):
                user["google_id"] = google_id
                user["updated_at"] = utc_now()
                self.users.upsert_item(user)
            elif user.get("google_id") != google_id:
                raise IdentityConflictError("E-postadressen er allerede koblet til en annen Google-konto.")
        else:
            user = self._new_user(
                email=normalized_email,
                first_name=first_name,
                last_name=last_name,
                google_id=google_id,
                picture=picture,
            )
            self._ensure_lookup(
                lookup_id=email_lookup_identifier(normalized_email), lookup_type="email", user=user
            )

        self._ensure_lookup(lookup_id=google_lookup_id, lookup_type="google_subject", user=user)
        return self._require_active(user)

    def resolve_email_identity(self, *, email: str, first_name: str = "Bonde") -> dict[str, Any]:
        normalized_email = normalize_email(email)
        user = self._find_by_email(normalized_email)
        if user is not None:
            return user
        user = self._new_user(email=normalized_email, first_name=first_name)
        self._ensure_lookup(
            lookup_id=email_lookup_identifier(normalized_email), lookup_type="email", user=user
        )
        return self._require_active(user)
