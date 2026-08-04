"""Self-service profile endpoints; e-mail identity remains read-only."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.api.dependencies.identity import CurrentIdentity, get_current_identity, require_csrf
from app.api.routes.auth import normalize_phone_number
from app.db.cosmos_client import get_audit_logs_container
from app.services.identity_service import IdentityService

router = APIRouter()
SUPPORTED_LANGUAGES = {"nb", "en"}
SUPPORTED_TIMEZONES = {"Europe/Oslo", "UTC"}
CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class ProfileResponse(BaseModel):
    user_id: str
    email: str
    email_verified: bool
    first_name: str
    last_name: str
    display_name: str
    phone_number: Optional[str] = None
    preferred_language: str
    timezone: str
    status: str
    profile_completed: bool
    terms_version: Optional[str] = None
    terms_accepted_at: Optional[str] = None
    privacy_version: Optional[str] = None
    privacy_accepted_at: Optional[str] = None


class ProfilePatch(BaseModel):
    first_name: Optional[str] = Field(default=None, max_length=80)
    last_name: Optional[str] = Field(default=None, max_length=80)
    display_name: Optional[str] = Field(default=None, max_length=120)
    phone_number: Optional[str] = None
    preferred_language: Optional[str] = None
    timezone: Optional[str] = None

    @field_validator("first_name", "last_name", "display_name")
    @classmethod
    def clean_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if CONTROL.search(value):
            raise ValueError("Feltet kan ikke inneholde kontrolltegn.")
        return value

    @field_validator("phone_number")
    @classmethod
    def clean_phone(cls, value: Optional[str]) -> Optional[str]:
        return normalize_phone_number(value) if value else None

    @field_validator("preferred_language")
    @classmethod
    def clean_language(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in SUPPORTED_LANGUAGES:
            raise ValueError("Språk må være nb eller en.")
        return value

    @field_validator("timezone")
    @classmethod
    def clean_timezone(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in SUPPORTED_TIMEZONES:
            raise ValueError("Tidssone støttes ikke.")
        return value


def profile_response(user: dict) -> ProfileResponse:
    return ProfileResponse(
        user_id=str(user["user_id"]), email=str(user["email"]), email_verified=bool(user.get("email_verified")),
        first_name=str(user.get("first_name") or ""), last_name=str(user.get("last_name") or ""),
        display_name=str(user.get("display_name") or " ".join([str(user.get("first_name") or ""), str(user.get("last_name") or "")]).strip()),
        phone_number=user.get("phone_number"), preferred_language=str(user.get("preferred_language") or "nb"),
        timezone=str(user.get("timezone") or "Europe/Oslo"), status=str(user.get("status") or "active"),
        profile_completed=bool(user.get("profile_completed")), terms_version=user.get("terms_version"),
        terms_accepted_at=user.get("terms_accepted_at"), privacy_version=user.get("privacy_version"), privacy_accepted_at=user.get("privacy_accepted_at"),
    )


def _audit(user_id: str) -> None:
    try:
        get_audit_logs_container().create_item({"id": f"profile-update:{user_id}:{datetime.now(timezone.utc).timestamp()}", "type": "audit_log", "event_type": "UserProfileUpdated", "farm_id": "identity", "actor_user_id": user_id, "created_at": datetime.now(timezone.utc).isoformat()})
    except Exception:
        pass


@router.get("/profile", response_model=ProfileResponse)
def get_profile(current: CurrentIdentity = Depends(get_current_identity)) -> ProfileResponse:
    return profile_response(current.user)


@router.patch("/profile", response_model=ProfileResponse)
def patch_profile(request: ProfilePatch, current: CurrentIdentity = Depends(require_csrf)) -> ProfileResponse:
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        return profile_response(current.user)
    try:
        user = IdentityService().update_profile(current.user, updates)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Kunne ikke lagre profilen akkurat nå.") from exc
    _audit(str(user["user_id"]))
    return profile_response(user)
