"""Small response models shared by the Identity HTTP routes."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.subscriptions.plans import get_plan


class IdentityUserResponse(BaseModel):
    user_id: str
    email: str
    first_name: str
    last_name: str = ""
    picture: Optional[str] = None
    phone_number: Optional[str] = None
    status: str


class SessionResponse(BaseModel):
    session_id: str
    created_at: str
    last_seen_at: Optional[str] = None
    expires_at: str
    current: bool = True


class AuthenticatedResponse(IdentityUserResponse):
    session: SessionResponse
    csrf_token: str
    message: str


class CsrfResponse(BaseModel):
    token: str
    expires_at: str


class FarmSnapshotResponse(BaseModel):
    id: str
    name: str
    org_number: str
    farm_status: str = "active"


class MembershipResponse(BaseModel):
    farm: FarmSnapshotResponse
    farm_role: str
    membership_status: str


class SubscriptionResponse(BaseModel):
    plan_code: str
    plan_version: str
    display_name: str
    subscription_status: str
    started_at: Optional[str] = None
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    trial_ends_at: Optional[str] = None
    grace_period_ends_at: Optional[str] = None
    cancel_at_period_end: bool = False
    canceled_at: Optional[str] = None


def subscription_response(subscription: dict) -> SubscriptionResponse:
    """Create the safe public subscription projection shared by API routes."""
    plan_code = str(subscription.get("plan_code") or "")
    plan_version = str(subscription.get("plan_version") or "")
    plan = get_plan(plan_version, plan_code)
    return SubscriptionResponse(
        plan_code=plan_code,
        plan_version=plan_version,
        display_name=plan.display_name if plan is not None else plan_code,
        subscription_status=str(subscription.get("subscription_status") or ""),
        started_at=subscription.get("started_at"),
        current_period_start=subscription.get("current_period_start"),
        current_period_end=subscription.get("current_period_end"),
        trial_ends_at=subscription.get("trial_ends_at"),
        grace_period_ends_at=subscription.get("grace_period_ends_at"),
        cancel_at_period_end=bool(subscription.get("cancel_at_period_end", False)),
        canceled_at=subscription.get("canceled_at"),
    )


class MeResponse(BaseModel):
    user: IdentityUserResponse
    session: SessionResponse
    csrf_token: str
    csrf: CsrfResponse
    memberships: List[MembershipResponse] = Field(default_factory=list)
    active_farm: Optional[FarmSnapshotResponse] = None
    subscription: Optional[SubscriptionResponse] = None
    entitlements: Dict[str, bool] = Field(default_factory=dict)


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
