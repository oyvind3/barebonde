"""Minimal signed-in bootstrap endpoint; tenancy is intentionally absent."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies.identity import CurrentIdentity, get_current_identity
from app.api.identity_models import (
    CsrfResponse,
    FarmSnapshotResponse,
    IdentityUserResponse,
    MembershipResponse,
    MeResponse,
    SessionResponse,
    subscription_response,
)
from app.services.entitlement_service import get_effective_entitlements
from app.services.membership_service import MembershipService
from app.services.session_service import SessionService
from app.services.subscription_service import SubscriptionService, SubscriptionUnavailableError

router = APIRouter()


def user_response(user: dict) -> IdentityUserResponse:
    return IdentityUserResponse(
        user_id=str(user["user_id"]),
        email=str(user["email"]),
        first_name=str(user.get("first_name") or "Bonde"),
        last_name=str(user.get("last_name") or ""),
        picture=user.get("picture"),
        phone_number=user.get("phone_number"),
        status=str(user.get("status") or "active"),
    )


def session_response(session: dict, *, current: bool = True) -> SessionResponse:
    return SessionResponse(
        session_id=str(session["id"]),
        created_at=str(session["created_at"]),
        last_seen_at=session.get("last_seen_at"),
        expires_at=str(session["expires_at"]),
        current=current,
    )


def _membership_response(membership: dict, service: MembershipService) -> MembershipResponse | None:
    snapshot = {
        "id": membership.get("farm_id"),
        "name": membership.get("farm_name"),
        "org_number": membership.get("org_number"),
        "farm_status": membership.get("farm_status", "active"),
    }
    if not snapshot["name"] or not snapshot["org_number"]:
        farm = service.get_farm(str(membership["farm_id"]))
        if farm is None:
            return None
        snapshot = {
            "id": farm["id"],
            "name": farm.get("name") or "",
            "org_number": farm.get("org_number") or "",
            "farm_status": farm.get("farm_status", "active"),
        }
    return MembershipResponse(
        farm=FarmSnapshotResponse(**snapshot),
        farm_role=str(membership["farm_role"]),
        membership_status=str(membership["membership_status"]),
    )


@router.get("/me", response_model=MeResponse)
def get_me(
    active_farm_id: Optional[str] = Query(default=None),
    current: CurrentIdentity = Depends(get_current_identity),
) -> MeResponse:
    """Return the session principal plus active, authoritative Farm memberships."""
    membership_service = MembershipService()
    memberships = [
        response
        for membership in membership_service.list_active_memberships_for_user(current.user["user_id"])
        if (response := _membership_response(membership, membership_service)) is not None
    ]
    active_farm = next((item.farm for item in memberships if item.farm.id == active_farm_id), None)
    if active_farm is None and memberships:
        active_farm = memberships[0].farm

    subscription = None
    entitlements: dict[str, bool] = {}
    if active_farm is not None:
        # Membership was established above.  Only the selected active Farm is
        # lazily initialized; this avoids an N+1 subscription write for users
        # who belong to several Farms.
        try:
            ensured = SubscriptionService().ensure_free_subscription(
                farm_id=active_farm.id,
                actor_user_id=str(current.user["user_id"]),
            )
        except SubscriptionUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Abonnementstjenesten er midlertidig utilgjengelig. Prøv igjen.",
            ) from exc
        subscription = subscription_response(ensured.subscription)
        entitlements = get_effective_entitlements(ensured.subscription)

    csrf_token = SessionService().csrf_token(current.raw_session_token)
    return MeResponse(
        user=user_response(current.user),
        session=session_response(current.session),
        csrf_token=csrf_token,
        csrf=CsrfResponse(token=csrf_token, expires_at=str(current.session["expires_at"])),
        memberships=memberships,
        active_farm=active_farm,
        subscription=subscription,
        entitlements=entitlements,
    )
