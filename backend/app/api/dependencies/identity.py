"""FastAPI dependencies for an authenticated server-managed session."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings
from app.core.security_tokens import IdentitySecurityConfigurationError, verify_hmac_value
from app.services.identity_service import DisabledUserError, IdentityError
from app.services.session_service import InvalidSessionError, SessionService


@dataclass(frozen=True)
class CurrentIdentity:
    raw_session_token: str
    session: dict
    user: dict


def get_current_identity(request: Request) -> CurrentIdentity:
    raw_session_token = request.cookies.get(settings.identity_cookie_name)
    if not raw_session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Innlogging kreves.")
    try:
        session, user = SessionService().get_session(raw_session_token)
    except IdentitySecurityConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except (InvalidSessionError, DisabledUserError, IdentityError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesjonen er ikke gyldig.") from exc
    return CurrentIdentity(raw_session_token=raw_session_token, session=session, user=user)


def require_csrf(
    request: Request, current: CurrentIdentity = Depends(get_current_identity)
) -> CurrentIdentity:
    try:
        expected = SessionService().csrf_token(current.raw_session_token)
    except IdentitySecurityConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not verify_hmac_value(expected, request.headers.get("X-CSRF-Token")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF-token mangler eller er ugyldig.")
    return current
