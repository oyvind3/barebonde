"""Passwordless e-mail authentication, onboarding, and Plunk email routes."""

from __future__ import annotations

import html
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, field_validator

from app.api.dependencies.identity import CurrentIdentity, get_current_identity, require_csrf
from app.api.identity_models import AuthenticatedResponse, SessionListResponse
from app.api.routes.me import session_response, user_response
from app.core.config import settings
from app.core.security_tokens import IdentitySecurityConfigurationError
from app.services.challenge_service import ChallengeService, InvalidChallengeError
from app.services.identity_service import DisabledUserError, IdentityConflictError, IdentityError, IdentityService
from app.services.session_service import InvalidSessionError, SessionService

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_PLUNK_API_URL = "https://next-api.useplunk.com/v1/send"
DEFAULT_FRONTEND_URL = "https://barebonde.no"
E164_PHONE_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


class EmailDeliveryError(Exception):
    """Raised when a transactional email cannot be submitted to Plunk."""


def normalize_phone_number(value: str) -> str:
    """Store phone numbers in a single E.164 representation.

    Norwegian eight-digit numbers are accepted for the existing onboarding form
    and normalized to +47. Other numbers must already include a country code.
    """
    normalized = re.sub(r"[\s().-]", "", value or "")
    if normalized.startswith("00"):
        normalized = f"+{normalized[2:]}"
    elif normalized.isdigit() and len(normalized) == 8:
        normalized = f"+47{normalized}"

    if not E164_PHONE_PATTERN.fullmatch(normalized):
        raise ValueError("Oppgi telefonnummer med landskode, for eksempel +47 912 34 567.")
    return normalized


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    address: Optional[str] = None
    onboarding_role: Optional[str] = None
    farm_name: Optional[str] = None
    org_number: Optional[str] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        return normalize_phone_number(value)

class AuthResponse(BaseModel):
    user_id: str
    email: str
    first_name: str
    last_name: str
    message: str
    email_sent: bool = False
    email_message: Optional[str] = None
    phone_number: Optional[str] = None


class MagicLinkRequest(BaseModel):
    email: EmailStr
    first_name: Optional[str] = "Bonde"


class MagicLinkVerifyRequest(BaseModel):
    token: str


def _get_plunk_config() -> tuple[str, str, str, Optional[str], str]:
    """Read Plunk configuration at request time without accepting public keys."""
    token = (
        os.getenv("PLUNK_SECRET_KEY")
        or os.getenv("PLUNK_SECRET_API_KEY")
        or os.getenv("PLUNK_API_TOKEN")
        or ""
    ).strip()
    from_email = (os.getenv("PLUNK_FROM_EMAIL") or "").strip()
    from_name = (os.getenv("PLUNK_FROM_NAME") or "Barebonde").strip()
    reply_to = (os.getenv("PLUNK_REPLY_TO_EMAIL") or "").strip() or None
    api_url = (os.getenv("PLUNK_API_URL") or DEFAULT_PLUNK_API_URL).strip()

    if not token:
        raise EmailDeliveryError("E-posttjenesten er ikke konfigurert med en Plunk secret key.")
    if not token.startswith("sk_"):
        raise EmailDeliveryError("Plunk-koden må være en secret key (sk_), ikke en public key (pk_).")
    if not from_email:
        raise EmailDeliveryError("PLUNK_FROM_EMAIL mangler. Den må være en avsender fra et verifisert domene i Plunk.")

    return token, from_email, from_name, reply_to, api_url


def _plunk_error_message(response: httpx.Response) -> str:
    """Return a safe, concise provider message without logging response bodies."""
    try:
        payload = response.json()
    except ValueError:
        return f"Plunk svarte med HTTP {response.status_code}."

    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        message = error.get("message")
    else:
        message = error or (payload.get("message") if isinstance(payload, dict) else None)
    return str(message or f"Plunk svarte med HTTP {response.status_code}.")


async def _send_plunk_email(*, to: str, subject: str, body: str) -> None:
    """Send one transactional email through Plunk's current public API."""
    token, from_email, from_name, reply_to, api_url = _get_plunk_config()
    sender: str | dict[str, str] = {"email": from_email, "name": from_name} if from_name else from_email
    payload: dict[str, Any] = {"to": to, "from": sender, "subject": subject, "body": body}
    if reply_to:
        payload["reply"] = reply_to

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                api_url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
                timeout=10.0,
            )
    except httpx.HTTPError as exc:
        raise EmailDeliveryError("Kunne ikke kontakte Plunk for å sende e-post.") from exc

    if response.status_code >= 400:
        raise EmailDeliveryError(_plunk_error_message(response))

    try:
        response_payload = response.json()
    except ValueError:
        response_payload = {}
    if isinstance(response_payload, dict) and response_payload.get("success") is False:
        raise EmailDeliveryError(_plunk_error_message(response))


def _frontend_url() -> str:
    return (os.getenv("FRONTEND_URL") or DEFAULT_FRONTEND_URL).rstrip("/")


def _identity_cookie_options() -> dict[str, Any]:
    """Use cross-site cookies in production and local-safe cookies in development."""
    secure = settings.identity_cookie_secure
    if secure is None:
        secure = settings.env.casefold() not in {"development", "test", "local"}
    return {
        "key": settings.identity_cookie_name,
        "httponly": True,
        "secure": secure,
        "samesite": "none" if secure else "lax",
        "path": "/",
        "max_age": settings.identity_session_ttl_seconds,
    }


def _set_session_cookie(response: Response, raw_session_token: str) -> None:
    response.set_cookie(value=raw_session_token, **_identity_cookie_options())


def _clear_session_cookie(response: Response) -> None:
    options = _identity_cookie_options()
    response.delete_cookie(
        key=options["key"],
        path=options["path"],
        secure=options["secure"],
        httponly=options["httponly"],
        samesite=options["samesite"],
    )


async def _send_confirmation_email(
    email: str,
    first_name: str,
    *,
    is_resend: bool = False,
    registration_profile: Optional[dict[str, Any]] = None,
) -> None:
    """Send the onboarding e-mail link used to verify the address."""
    # Fail before creating a reusable challenge if delivery is not configured.
    _get_plunk_config()
    safe_name = html.escape(first_name or "Bonde")
    raw_token = ChallengeService().create_email_registration_challenge(
        email=email, registration_profile=registration_profile
    )
    action = "Du ba om en ny bekreftelseslenke." if is_resend else "Takk for at du oppretter konto hos Barebonde."
    await _send_plunk_email(
        to=email,
        subject="Bekreft e-postadressen din hos Barebonde",
        body=(
            f"<h1>Hei {safe_name}!</h1><p>{action}</p>"
            f"<p><a href='{_frontend_url()}/farm/setup?token={raw_token}'>Bekreft e-postadressen</a></p>"
            f"<p>Lenken kan brukes én gang og utløper om {settings.identity_magic_link_ttl_seconds // 60} minutter.</p>"
        ),
    )


def _upsert_existing_user(
    users_container: Any,
    user_data: dict[str, Any],
    *,
    email: str,
    first_name: str,
    last_name: str,
    phone_number: Optional[str] = None,
    address: Optional[str] = None,
    onboarding_role: Optional[str] = None,
    phone_verified: Optional[bool] = None,
) -> dict[str, Any]:
    """Update profile fields while preserving the immutable Cosmos partition key."""
    user_data.update(
        {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
        }
    )
    if phone_number is not None:
        user_data["phone_number"] = phone_number
    if address is not None:
        user_data["address"] = address
    if onboarding_role is not None:
        user_data["onboarding_role"] = onboarding_role
    if phone_verified is not None:
        user_data["phone_verified"] = phone_verified
    user_data["email_normalized"] = email.strip().casefold()
    user_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    users_container.upsert_item(user_data)
    return user_data


@router.post("/resend-confirmation")
async def resend_confirmation_email(req: MagicLinkRequest) -> dict[str, str]:
    """Resend a confirmation email and report actual provider failures to the UI."""
    try:
        await _send_confirmation_email(str(req.email), req.first_name or "Bonde", is_resend=True)
    except (EmailDeliveryError, IdentitySecurityConfigurationError, IdentityError) as exc:
        logger.warning("Confirmation resend failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return {"status": "ok", "message": "Bekreftelses-e-post er sendt på nytt."}


@router.post("/register")
async def register_user(req: RegisterRequest) -> AuthResponse:
    """Legacy farm-setup entry point that starts registration only.

    It keeps the established response contract while making verification the
    first point at which a User document can be created.
    """
    email = str(req.email).lower()
    first_name = req.first_name.strip()
    last_name = req.last_name.strip()
    address = (req.address or "").strip() or None
    onboarding_role = (req.onboarding_role or "").strip() or None

    try:
        await _send_confirmation_email(
            email,
            first_name or "Bonde",
            registration_profile={
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": req.phone_number,
                "address": address,
                "onboarding_role": onboarding_role,
            },
        )
    except IdentityError as exc:
        if str(exc) == "account_already_exists":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="account_already_exists") from exc
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kunne ikke kontrollere kontoen akkurat nå.",
        ) from exc
    except EmailDeliveryError as exc:
        logger.warning("Registration email was not sent: %s", exc)
        return AuthResponse(
            user_id="",
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=req.phone_number,
            email_sent=False,
            email_message=str(exc),
            message="Kontoen er ikke opprettet fordi bekreftelses-e-posten ikke kunne sendes.",
        )

    return AuthResponse(
        user_id="",
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone_number=req.phone_number,
        email_sent=True,
        email_message="Bekreftelses-e-post er sendt.",
        message="Bekreft e-postadressen for å opprette brukeren.",
    )


@router.post("/magic-link")
async def send_magic_link(req: MagicLinkRequest) -> dict[str, str]:
    """Create a single-use e-mail login challenge and submit it through Plunk."""
    try:
        # Avoid persisting a valid challenge when no e-mail provider is configured.
        _get_plunk_config()
        raw_token = ChallengeService().create_email_login_challenge(
            email=str(req.email), first_name=req.first_name or "Bonde"
        )
        login_url = f"{_frontend_url()}/login?token={raw_token}"
        await _send_plunk_email(
            to=str(req.email),
            subject="Din innloggingslenke til Barebonde",
            body=(
                f"<h1>Logg inn på Barebonde</h1>"
                f"<p><a href='{login_url}'>Logg inn i Barebonde</a></p>"
                f"<p>Lenken kan brukes én gang og utløper om 15 minutter.</p>"
            ),
        )
    except (EmailDeliveryError, IdentitySecurityConfigurationError, IdentityError) as exc:
        logger.warning("Magic-link email was not sent: %s", exc)
        if isinstance(exc, IdentityError) and str(exc) == "account_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="account_not_found") from exc
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return {"status": "ok", "message": "Innloggingslenke sendt på e-post."}


@router.post("/email/request")
async def request_login_email(req: MagicLinkRequest) -> dict[str, str]:
    """Send a login link only for an already registered identity."""
    try:
        _get_plunk_config()
        raw_token = ChallengeService().create_email_login_challenge(email=str(req.email))
    except IdentityError as exc:
        if str(exc) == "account_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="account_not_found") from exc
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Kunne ikke kontrollere kontoen akkurat nå.") from exc
    try:
        await _send_plunk_email(to=str(req.email), subject="Din innloggingslenke til Barebonde", body=f"<p><a href='{_frontend_url()}/login?token={raw_token}'>Logg inn i Barebonde</a></p>")
    except EmailDeliveryError as exc:
        logger.warning("Login email was not sent: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Kunne ikke sende e-post akkurat nå.") from exc
    return {"status": "ok", "message": "Innloggingslenke sendt på e-post."}


@router.post("/register/email/request")
async def request_registration_email(req: MagicLinkRequest) -> dict[str, str]:
    """Start explicit registration without creating a User before verification."""
    try:
        _get_plunk_config()
        raw_token = ChallengeService().create_email_registration_challenge(email=str(req.email))
    except IdentityError as exc:
        if str(exc) == "account_already_exists":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="account_already_exists") from exc
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Kunne ikke kontrollere kontoen akkurat nå.") from exc
    try:
        await _send_plunk_email(to=str(req.email), subject="Bekreft og opprett Barebonde-konto", body=f"<p><a href='{_frontend_url()}/login?token={raw_token}&flow=register'>Bekreft e-postadressen</a></p>")
    except EmailDeliveryError as exc:
        logger.warning("Registration email was not sent: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Kunne ikke sende e-post akkurat nå.") from exc
    return {"status": "ok", "message": "Vi har sendt en lenke for å bekrefte e-postadressen og opprette kontoen."}


@router.post("/magic-link/verify", response_model=AuthenticatedResponse)
async def verify_magic_link(req: MagicLinkVerifyRequest, response: Response) -> AuthenticatedResponse:
    """Consume an e-mail challenge exactly once and start a server-managed session."""
    if not req.token or not req.token.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Innloggingslenke mangler.")
    try:
        user = ChallengeService().consume_email_challenge(req.token)
        raw_session_token, session = SessionService().create_session(user)
    except InvalidChallengeError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except (IdentitySecurityConfigurationError, IdentityError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    _set_session_cookie(response, raw_session_token)
    return AuthenticatedResponse(
        **user_response(user).model_dump(),
        session=session_response(session),
        csrf_token=SessionService().csrf_token(raw_session_token),
        message="Innlogging med e-postlenke var vellykket.",
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, current: CurrentIdentity = Depends(require_csrf)) -> Response:
    """Revoke only the current server-side session and expire its browser cookie."""
    SessionService().revoke_session(user=current.user, session_id=current.session["id"])
    _clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/sessions", response_model=SessionListResponse)
def list_sessions(current: CurrentIdentity = Depends(get_current_identity)) -> SessionListResponse:
    """List this user's non-revoked sessions without exposing secret token material."""
    sessions = SessionService().list_sessions(current.user, current.raw_session_token)
    return SessionListResponse(sessions=sessions)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(
    session_id: str, response: Response, current: CurrentIdentity = Depends(require_csrf)
) -> Response:
    """Revoke one of the current user's sessions; clearing cookie when it is current."""
    service = SessionService()
    try:
        revoked = service.revoke_session(user=current.user, session_id=session_id)
    except InvalidSessionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesjonen finnes ikke.")
    if session_id == current.session["id"]:
        _clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
