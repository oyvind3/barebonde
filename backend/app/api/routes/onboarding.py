"""Server-derived, resumable onboarding state stored additively on User."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies.identity import CurrentIdentity, get_current_identity, require_csrf
from app.services.identity_service import IdentityService
from app.services.membership_service import MembershipService

router = APIRouter()
CURRENT_TERMS_VERSION = "2026-08"
INTERESTS = {"bilag", "bokforing", "rapporter", "fakturering", "ehf", "maskiner", "vedlikehold", "oppgaver", "avtaler_frister"}
# Pilot-onboarding teller bare steg som faktisk kan fullføres.  Bankkonto er et
# betalingssteg som ikke inngår i piloten, og "summary" er en terminal markør,
# ikke et eget steg.
STEPS = ("identity", "profile", "farm", "interests")


class OnboardingPatch(BaseModel):
    current_step: Optional[str] = None
    interests: Optional[list[str]] = Field(default=None, max_length=9)
    accept_terms: bool = False
    accept_privacy: bool = False


def onboarding_status(user: dict, memberships: list[dict]) -> dict:
    completed = ["identity"] if user.get("email_verified") else []
    if user.get("first_name") and user.get("last_name") and user.get("terms_accepted_at") and user.get("privacy_accepted_at"):
        completed.append("profile")
    if memberships:
        completed.append("farm")
    if user.get("onboarding_interests"):
        completed.append("interests")
    current = str(user.get("onboarding_current_step") or next((step for step in STEPS if step not in completed), "summary"))
    return {"completed": bool(user.get("onboarding_completed_at")), "current_step": current, "completed_steps": completed, "completion_percent": round(len(completed) / len(STEPS) * 100), "total_steps": len(STEPS), "interests": list(user.get("onboarding_interests") or [])}


@router.get("/onboarding")
def get_onboarding(current: CurrentIdentity = Depends(get_current_identity)) -> dict:
    memberships = MembershipService().list_active_memberships_for_user(str(current.user["user_id"]))
    return onboarding_status(current.user, memberships)


@router.patch("/onboarding")
def patch_onboarding(request: OnboardingPatch, current: CurrentIdentity = Depends(require_csrf)) -> dict:
    if request.current_step is not None and request.current_step not in STEPS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ukjent onboardingsteg.")
    if request.interests is not None and not set(request.interests).issubset(INTERESTS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ukjent bruksområde.")
    now = datetime.now(timezone.utc).isoformat()
    updates: dict = {}
    if request.current_step is not None:
        updates["onboarding_current_step"] = request.current_step
    if request.interests is not None:
        updates["onboarding_interests"] = list(dict.fromkeys(request.interests))
    if request.accept_terms:
        updates.update({"terms_version": CURRENT_TERMS_VERSION, "terms_accepted_at": now})
    if request.accept_privacy:
        updates.update({"privacy_version": CURRENT_TERMS_VERSION, "privacy_accepted_at": now})
    user = IdentityService().update_profile(current.user, updates)
    memberships = MembershipService().list_active_memberships_for_user(str(user["user_id"]))
    return onboarding_status(user, memberships)


@router.post("/onboarding/complete")
def complete_onboarding(current: CurrentIdentity = Depends(require_csrf)) -> dict:
    memberships = MembershipService().list_active_memberships_for_user(str(current.user["user_id"]))
    state = onboarding_status(current.user, memberships)
    required = {"identity", "profile", "farm"}
    if not required.issubset(state["completed_steps"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fullfør konto, profil og virksomhet før onboarding avsluttes.")
    user = IdentityService().update_profile(current.user, {"onboarding_completed_at": datetime.now(timezone.utc).isoformat(), "onboarding_current_step": "summary"})
    return onboarding_status(user, memberships)
