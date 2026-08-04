"""Minimal signed-in bootstrap endpoint; tenancy is intentionally absent."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies.identity import CurrentIdentity, get_current_identity
from app.api.identity_models import IdentityUserResponse, MeResponse, SessionResponse
from app.services.session_service import SessionService

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


@router.get("/me", response_model=MeResponse)
def get_me(current: CurrentIdentity = Depends(get_current_identity)) -> MeResponse:
    """Return only the authenticated user and current session.

    Farms, roles, subscriptions and permissions are deliberately not added
    until their bounded contexts are implemented.
    """
    return MeResponse(
        user=user_response(current.user),
        session=session_response(current.session),
        csrf_token=SessionService().csrf_token(current.raw_session_token),
    )
