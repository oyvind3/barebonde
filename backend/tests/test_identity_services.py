import os
from datetime import datetime, timedelta, timezone

import pytest
from azure.cosmos import exceptions

os.environ.setdefault("COSMOS_DB_CONNECTION_STRING", "not-used-in-unit-tests")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("IDENTITY_HMAC_KEY", "test-identity-hmac-key")

from app.services.challenge_service import ChallengeService, InvalidChallengeError
from app.services.identity_service import DisabledUserError, IdentityError, IdentityService
from app.services.session_service import InvalidSessionError, SessionService


class MemoryContainer:
    def __init__(self):
        self.items = {}

    def create_item(self, item):
        if item["id"] in self.items:
            raise exceptions.CosmosResourceExistsError(message="exists", response=None)
        self.items[item["id"]] = dict(item)
        return item

    def upsert_item(self, item):
        self.items[item["id"]] = dict(item)
        return item

    def read_item(self, item, partition_key):
        value = self.items.get(item)
        if not value or partition_key not in {
            value.get("better_auth_id"),
            value.get("lookup_partition_id"),
            value.get("challenge_partition_id"),
            value.get("session_partition_id"),
        }:
            raise exceptions.CosmosResourceNotFoundError(message="missing", response=None)
        return dict(value)

    def replace_item(self, item, body, **_):
        if item not in self.items:
            raise exceptions.CosmosResourceNotFoundError(message="missing", response=None)
        self.items[item] = dict(body)
        return body

    def query_items(self, *, query, parameters, **_):
        value = parameters[0]["value"]
        if "email_normalized" in query:
            return [item for item in self.items.values() if item.get("email_normalized") == value]
        if " c.email =" in query:
            return [item for item in self.items.values() if item.get("email") == value]
        if "user_id" in query:
            return [item for item in self.items.values() if item.get("user_id") == value]
        return []


def identity_service():
    return IdentityService(users_container=MemoryContainer(), lookups_container=MemoryContainer())


def test_email_identity_uses_an_opaque_lookup_without_storing_email_in_the_lookup_document():
    identity = identity_service()

    user = identity.resolve_email_identity(email=" Ola@Example.com ", first_name="Ola")

    assert user["user_id"] == user["id"]
    assert user["better_auth_id"] != user["email"]
    lookup = next(iter(identity.lookups.items.values()))
    assert lookup["lookup_type"] == "email"
    assert "ola@example.com" not in str(lookup).lower()
    assert len(lookup["id"]) == 64


def test_email_challenge_is_opaque_expires_and_can_only_be_consumed_once():
    identity = identity_service()
    challenges = MemoryContainer()
    service = ChallengeService(challenges_container=challenges, identity_service=identity)

    identity.resolve_email_identity(email="ola@example.com", first_name="Ola")
    token = service.create_email_login_challenge(email="ola@example.com", first_name="Ola")
    challenge = next(iter(challenges.items.values()))
    assert token not in str(challenge)
    assert "ola@example.com" not in str(challenge).lower()

    user = service.consume_email_login_challenge(token)
    assert user["email"] == "ola@example.com"
    with pytest.raises(InvalidChallengeError):
        service.consume_email_login_challenge(token)

    identity.resolve_email_identity(email="kari@example.com")
    expired_token = service.create_email_login_challenge(email="kari@example.com")
    expired = next(item for item in challenges.items.values() if not item.get("consumed_at"))
    expired["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    challenges.upsert_item(expired)
    with pytest.raises(InvalidChallengeError):
        service.consume_email_login_challenge(expired_token)


def test_login_lookup_does_not_create_a_user_but_registration_waits_for_verification():
    identity = identity_service()
    challenges = MemoryContainer()
    service = ChallengeService(challenges_container=challenges, identity_service=identity)

    with pytest.raises(IdentityError, match="account_not_found"):
        service.create_email_login_challenge(email="ny@example.com")
    assert identity.users.items == {}

    token = service.create_email_registration_challenge(
        email="ny@example.com",
        registration_profile={"first_name": "Ny", "last_name": "Bonde", "phone_number": "+4791234567"},
    )
    assert identity.users.items == {}
    user = service.consume_email_challenge(token)

    assert user["email"] == "ny@example.com"
    assert user["last_name"] == "Bonde"
    assert user["phone_number"] == "+4791234567"
    assert user["email_verified"] is True


def test_session_persists_only_a_digest_and_revocation_invalidates_it():
    identity = identity_service()
    user = identity.resolve_email_identity(email="ola@example.com")
    sessions = MemoryContainer()
    service = SessionService(sessions_container=sessions, identity_service=identity)

    raw_token, session = service.create_session(user)
    persisted = next(iter(sessions.items.values()))
    assert raw_token not in str(persisted)
    assert persisted["id"] != raw_token
    assert service.csrf_token(raw_token) != raw_token
    assert service.get_session(raw_token)[1]["user_id"] == user["user_id"]

    assert service.revoke_session(user=user, session_id=session["id"])
    with pytest.raises(InvalidSessionError):
        service.get_session(raw_token)


def test_disabled_user_cannot_create_or_use_a_session():
    identity = identity_service()
    user = identity.resolve_email_identity(email="ola@example.com")
    user["status"] = "disabled"
    identity.users.upsert_item(user)
    service = SessionService(sessions_container=MemoryContainer(), identity_service=identity)

    with pytest.raises(DisabledUserError):
        service.create_session(user)
