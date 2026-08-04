import os

import pytest

os.environ.setdefault("COSMOS_DB_CONNECTION_STRING", "not-used-in-unit-tests")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("IDENTITY_HMAC_KEY", "test-identity-hmac-key")

from app.services.invitation_service import InvitationError, InvitationService


def test_invitation_identifiers_are_deterministic_and_do_not_expose_email():
    first = InvitationService.invitation_id("farm-a", " Ola@Example.no ")
    second = InvitationService.invitation_id("farm-a", "ola@example.no")

    assert first == second
    assert "ola@example.no" not in first


def test_invitation_token_hash_does_not_contain_the_raw_secret():
    digest = InvitationService.token_hash("raw-invitation-token")

    assert digest != "raw-invitation-token"
    assert len(digest) == 64


def test_only_manager_and_staff_are_invitable_without_touching_storage():
    service = InvitationService.__new__(InvitationService)

    with pytest.raises(InvitationError, match="invalid_member_role"):
        service.create_invitation(farm={"id": "farm-a"}, email="ola@example.no", role="owner", actor_user_id="user-a")
