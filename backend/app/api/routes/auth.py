"""Password and passwordless e-mail authentication, onboarding, and Plunk email routes."""

from __future__ import annotations

import html
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, field_validator, field_serializer

from app.api.dependencies.identity import CurrentIdentity, get_current_identity, require_csrf
from app.api.identity_models import AuthenticatedResponse, SessionListResponse
from app.api.routes.me import session_response, user_response
from app.core.config import settings
from app.core.security_tokens import IdentitySecurityConfigurationError
from app.services.challenge_service import ChallengeService, InvalidChallengeError
from app.services.email_service import (
    EmailDeliveryError,
    _get_plunk_config,
    send_transactional_email,
    validate_plunk_configured,
)
from app.services.identity_service import DisabledUserError, IdentityConflictError, IdentityError, IdentityService
from app.services.password_service import PasswordService
from app.services.session_service import InvalidSessionError, SessionService

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_FRONTEND_URL = "https://barebonde.no"
E164_PHONE_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


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
    password: Optional[str] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        return normalize_phone_number(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            if len(value) < 8:
                raise ValueError("Passordet må være minst 8 tegn langt.")
            if len(value) > 72:
                raise ValueError("Passordet kan ikke være lengre enn 72 tegn.")
        return value


class LoginWithPasswordRequest(BaseModel):
    """Request model for password-based login."""
    email: EmailStr
    password: str


class SetPasswordRequest(BaseModel):
    """Request model for setting a password (during onboarding or profile update)."""
    password: str
    confirm_password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Passordet må være minst 8 tegn langt.")
        if len(value) > 72:
            raise ValueError("Passordet kan ikke være lengre enn 72 tegn.")
        return value

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, value: str, info) -> str:
        # We'll validate matching in the route handler
        return value


class ForgotPasswordRequest(BaseModel):
    """Request model for initiating a password reset."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request model for resetting password with a token."""
    token: str
    new_password: str
    confirm_new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Passordet må være minst 8 tegn langt.")
        if len(value) > 72:
            raise ValueError("Passordet kan ikke være lengre enn 72 tegn.")
        return value

    @field_validator("confirm_new_password")
    @classmethod
    def validate_confirm_new_password(cls, value: str, info) -> str:
        # We'll validate matching in the route handler
        return value


class ChangePasswordRequest(BaseModel):
    """Request model for changing an existing password.
    
    Requires the current password for verification before setting a new password.
    """
    current_password: str
    new_password: str
    confirm_new_password: str

    @field_validator("current_password")
    @classmethod
    def validate_current_password(cls, value: str) -> str:
        if not value:
            raise ValueError("Nåværende passord må oppgis.")
        return value

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Passordet må være minst 8 tegn langt.")
        if len(value) > 72:
            raise ValueError("Passordet kan ikke være lengre enn 72 tegn.")
        return value

    @field_validator("confirm_new_password")
    @classmethod
    def validate_confirm_new_password(cls, value: str, info) -> str:
        # We'll validate matching in the route handler
        return value


class AuthResponse(BaseModel):
    user_id: str
    email: str
    first_name: str
    last_name: str
    message: str
    email_sent: bool = False
    email_message: Optional[str] = None
    phone_number: Optional[str] = None
    has_password: bool = False


class MagicLinkRequest(BaseModel):
    email: EmailStr
    first_name: Optional[str] = "Bonde"
    return_to: Optional[str] = None


class MagicLinkVerifyRequest(BaseModel):
    token: str


async def _send_plunk_email(*, to: str, subject: str, body: str) -> None:
    """Send one transactional email through Plunk's current public API."""
    await send_transactional_email(to=to, subject=subject, body=body)


def _frontend_url() -> str:
    return (os.getenv("FRONTEND_URL") or DEFAULT_FRONTEND_URL).rstrip("/")


def _safe_return_to(value: Optional[str]) -> str:
    """Allow only known internal paths; never reflect an external redirect."""
    candidate = (value or "").strip()
    if candidate.startswith("/invitations/accept?intent=") or candidate in {"/dashboard", "/onboarding"}:
        return candidate
    return "/onboarding"


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
    Password is optional during registration and will be set later if provided.
    """
    email = str(req.email).lower()
    first_name = req.first_name.strip()
    last_name = req.last_name.strip()
    address = (req.address or "").strip() or None
    onboarding_role = (req.onboarding_role or "").strip() or None
    password = req.password

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
                "password": password,  # Will be hashed during verification
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
        has_password=bool(password),
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
        return_to = _safe_return_to(req.return_to)
        await _send_plunk_email(to=str(req.email), subject="Din innloggingslenke til Barebonde", body=f"<p><a href='{_frontend_url()}/login?token={raw_token}&returnTo={html.escape(return_to, quote=True)}'>Logg inn i Barebonde</a></p>")
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
        return_to = _safe_return_to(req.return_to)
        await _send_plunk_email(to=str(req.email), subject="Bekreft og opprett Barebonde-konto", body=f"<p><a href='{_frontend_url()}/login?token={raw_token}&flow=register&returnTo={html.escape(return_to, quote=True)}'>Bekreft e-postadressen</a></p>")
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


@router.post("/login/password")
async def login_with_password(req: LoginWithPasswordRequest, response: Response) -> AuthenticatedResponse:
    """Authenticate a user with email and password.
    
    This is the primary login method. Magic link login remains as a fallback.
    """
    email = str(req.email).lower()
    password = req.password
    
    # Find the user by email
    identity_service = IdentityService()
    try:
        user = identity_service.find_existing_email_identity(email)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Feil e-postadresse eller passord.",
            )
    except IdentityError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Feil e-postadresse eller passord.",
        ) from None
    
    # Check if user has a password set
    password_hash = user.get("password_hash")
    if not password_hash:
        # User exists but hasn't set a password yet - offer magic link instead
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Du har ikke satt et passord ennå. Bruk innloggingslenke på e-post.",
        )
    
    # Verify the password
    if not PasswordService.verify_password(password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Feil e-postadresse eller passord.",
        )
    
    # Create session
    try:
        raw_session_token, session = SessionService().create_session(user)
    except (IdentitySecurityConfigurationError, IdentityError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kunne ikke opprette sesjon akkurat nå.",
        ) from exc
    
    _set_session_cookie(response, raw_session_token)
    return AuthenticatedResponse(
        **user_response(user).model_dump(),
        session=session_response(session),
        csrf_token=SessionService().csrf_token(raw_session_token),
        message="Innlogging med passord var vellykket.",
    )


@router.post("/password/set")
async def set_password(req: SetPasswordRequest, current: CurrentIdentity = Depends(require_csrf)) -> dict[str, str]:
    """Set or update the user's password.
    
    This can be used during onboarding or later in profile settings.
    Returns 409 Conflict if the user already has a password set.
    """
    # Prevent overwriting an existing password via this endpoint
    if current.user.get("password_hash"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Passord er allerede satt. Bruk endre passord for å oppdatere.",
        )
    
    if req.password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passordene stemmer ikke overens.",
        )
    
    try:
        password_hash = PasswordService.hash_password(req.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    
    now = datetime.now(timezone.utc).isoformat()
    updates = {
        "password_hash": password_hash,
        "password_set_at": now,
    }
    
    user = IdentityService().update_profile(current.user, updates)
    
    return {
        "status": "ok",
        "message": "Passord er lagret.",
        "has_password": True,
    }


@router.post("/password/change")
async def change_password(
    req: ChangePasswordRequest,
    current: CurrentIdentity = Depends(require_csrf),
) -> dict[str, str]:
    """Change the user's password (requires knowing current password).
    
    Validates the current password before allowing a change.
    Revokes all other sessions for security after password change.
    """
    # Verify current password
    password_hash = current.user.get("password_hash")
    if not password_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Passord er ikke satt. Bruk sett passord først.",
        )
    
    if not PasswordService.verify_password(req.current_password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nåværende passord er feil.",
        )
    
    if req.new_password != req.confirm_new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passordene stemmer ikke overens.",
        )
    
    try:
        new_password_hash = PasswordService.hash_password(req.new_password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    
    now = datetime.now(timezone.utc).isoformat()
    updates = {
        "password_hash": new_password_hash,
        "password_set_at": now,
    }
    
    user = IdentityService().update_profile(current.user, updates)
    
    # Revoke all other sessions for security
    session_service = SessionService()
    revoked_count = session_service.revoke_other_sessions(user["id"], exclude_session_id=current.session["id"])
    
    logger.info(
        "Password changed for user %s (%s), revoked %d other sessions",
        user["id"],
        user.get("email", ""),
        revoked_count,
    )
    
    return {
        "status": "ok",
        "message": "Passord er endret. Andre sesjoner er logget ut.",
        "has_password": True,
    }


@router.post("/password/forgot")
async def forgot_password(req: ForgotPasswordRequest) -> dict[str, str]:
    """Initiate password reset by sending a reset link to the user's email.
    
    This creates a password reset challenge and sends an email with a reset link.
    The link expires after a configured TTL (default 1 hour).
    """
    email = str(req.email).lower()
    
    identity_service = IdentityService()
    try:
        user = identity_service.find_existing_email_identity(email)
        if user is None:
            # Don't reveal if email exists or not (security best practice)
            return {
                "status": "ok",
                "message": "Hvis e-postadressen finnes i systemet, vil du motta en lenke for å nullstille passordet.",
            }
    except IdentityError:
        return {
            "status": "ok",
            "message": "Hvis e-postadressen finnes i systemet, vil du motta en lenke for å nullstille passordet.",
        }
    
    # Check if user has a password set (only makes sense for users with passwords)
    if not user.get("password_hash"):
        return {
            "status": "ok",
            "message": "Du har ikke satt et passord ennå. Bruk innloggingslenke på e-post.",
        }
    
    # Create password reset challenge
    try:
        raw_token = ChallengeService().create_password_reset_challenge(email=email)
    except (IdentitySecurityConfigurationError, IdentityError) as exc:
        logger.warning("Failed to create password reset challenge: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kunne ikke opprette nullstillingslenke akkurat nå.",
        ) from exc
    
    # Send reset email
    safe_name = html.escape(user.get("first_name", "Bonde") or "Bonde")
    reset_url = f"{_frontend_url()}/auth/reset-password?token={raw_token}"
    
    try:
        await _send_plunk_email(
            to=email,
            subject="Nullstill ditt passord hos Barebonde",
            body=(
                f"<h1>Hei {safe_name}!</h1>"
                f"<p>Du ba om å nullstille passordet ditt.</p>"
                f"<p><a href='{reset_url}'>Nullstill passord</a></p>"
                f"<p>Lenken kan brukes én gang og utløper om {settings.identity_magic_link_ttl_seconds // 60} minutter.</p>"
                f"<p>Hvis du ikke ba om dette, kan du ignorere denne e-posten.</p>"
            ),
        )
    except EmailDeliveryError as exc:
        logger.warning("Password reset email failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kunne ikke sende e-post for nullstilling av passord.",
        ) from exc
    
    return {
        "status": "ok",
        "message": "Hvis e-postadressen finnes i systemet, vil du motta en lenke for å nullstille passordet.",
    }


@router.post("/password/reset")
async def reset_password(req: ResetPasswordRequest, response: Response) -> dict[str, str]:
    """Reset password using a valid reset token.
    
    This verifies the reset token and sets a new password.
    All existing sessions are revoked for security.
    """
    # Verify the reset token and get user info
    challenge_service = ChallengeService()
    try:
        challenge_data = challenge_service.verify_password_reset_challenge(req.token)
        email = challenge_data.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ugyldig eller utløpt nullstillingslenke.",
            )
    except (InvalidChallengeError, IdentityError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ugyldig eller utløpt nullstillingslenke.",
        ) from exc
    
    # Find the user
    identity_service = IdentityService()
    try:
        user = identity_service.find_existing_email_identity(str(email))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ugyldig nullstillingslenke.",
            )
    except IdentityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ugyldig nullstillingslenke.",
        ) from None
    
    # Validate passwords match
    if req.new_password != req.confirm_new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passordene stemmer ikke overens.",
        )
    
    # Hash and set new password
    try:
        password_hash = PasswordService.hash_password(req.new_password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    
    now = datetime.now(timezone.utc).isoformat()
    updates = {
        "password_hash": password_hash,
        "password_set_at": now,
    }
    
    user = IdentityService().update_profile(user, updates)
    
    # Revoke all sessions including the current one (force re-login)
    session_service = SessionService()
    session_service.revoke_all_sessions(user["id"])
    
    # Invalidate the used challenge
    challenge_service.invalidate_challenge(req.token)
    
    logger.info("Password reset completed for user %s (%s)", user["id"], user.get("email", ""))
    
    return {
        "status": "ok",
        "message": "Passordet er nullstilt. Vennligst logg inn med nytt passord.",
        "has_password": True,
    }
