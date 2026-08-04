"""User authentication, onboarding, Plunk email, and Google OAuth routes."""

from __future__ import annotations

import html
import logging
import os
import re
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token
from pydantic import BaseModel, EmailStr, field_validator, model_validator

from app.db.cosmos_client import get_users_container
from app.db.cosmos_models import User

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_PLUNK_API_URL = "https://next-api.useplunk.com/v1/send"
DEFAULT_FRONTEND_URL = "https://salmon-ocean-076260203.7.azurestaticapps.net"
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
    password: Optional[str] = None
    google_token: Optional[str] = None
    phone_number: str
    address: Optional[str] = None
    onboarding_role: Optional[str] = None
    farm_name: Optional[str] = None
    org_number: Optional[str] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        return normalize_phone_number(value)

    @model_validator(mode="after")
    def validate_identity_method(self) -> "RegisterRequest":
        has_password = bool((self.password or "").strip())
        has_google_token = bool((self.google_token or "").strip())
        if has_password == has_google_token:
            raise ValueError("Velg enten passord eller Google-innlogging for registreringen.")
        return self


class AuthResponse(BaseModel):
    user_id: str
    email: str
    first_name: str
    last_name: str
    message: str
    email_sent: bool = False
    email_message: Optional[str] = None
    phone_number: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MagicLinkRequest(BaseModel):
    email: EmailStr
    first_name: Optional[str] = "Bonde"


class GoogleTokenRequest(BaseModel):
    token: str


class GoogleConfigResponse(BaseModel):
    client_id: str


class GoogleAuthResponse(BaseModel):
    user_id: str
    email: str
    first_name: str
    last_name: str = ""
    picture: Optional[str] = None
    message: str


class GoogleIdentityResponse(BaseModel):
    """Verified Google claims used to defer Cosmos persistence until onboarding ends."""

    google_id: str
    email: str
    first_name: str
    last_name: str = ""
    picture: Optional[str] = None


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


async def _send_confirmation_email(email: str, first_name: str, *, is_resend: bool = False) -> None:
    safe_name = html.escape(first_name or "Bonde")
    action = "Du ba om å få bekreftelseslenken på nytt." if is_resend else "Takk for at du opprettet konto hos Barebonde."
    await _send_plunk_email(
        to=email,
        subject="Bekreft din e-post for Barebonde",
        body=(
            f"<h1>Hei {safe_name}!</h1><p>{action}</p>"
            f"<p><a href='{_frontend_url()}/dashboard'>Åpne Barebonde</a></p>"
        ),
    )


def _find_user(users_container: Any, field: str, value: str) -> Optional[dict[str, Any]]:
    """Find one user without interpolating user-controlled values into Cosmos SQL."""
    query = f"SELECT * FROM c WHERE c.{field} = @value"
    users = list(
        users_container.query_items(
            query=query,
            parameters=[{"name": "@value", "value": value}],
            enable_cross_partition_query=True,
        )
    )
    return users[0] if users else None


def _google_identity_from_payload(payload: dict[str, Any]) -> GoogleIdentityResponse:
    google_id = str(payload.get("sub") or "")
    email = str(payload.get("email") or "").lower()
    if not google_id or not email:
        raise ValueError("Google-tokenet mangler brukeridentitet.")
    if payload.get("email_verified") is False:
        raise ValueError("Google har ikke bekreftet e-postadressen.")

    return GoogleIdentityResponse(
        google_id=google_id,
        email=email,
        first_name=str(payload.get("given_name") or payload.get("name") or "Bonde"),
        last_name=str(payload.get("family_name") or ""),
        picture=str(payload["picture"]) if payload.get("picture") else None,
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
    google_id: Optional[str] = None,
    picture: Optional[str] = None,
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
    if google_id is not None:
        user_data["google_id"] = google_id
    if picture is not None:
        user_data["picture"] = picture
    if phone_verified is not None:
        user_data["phone_verified"] = phone_verified

    users_container.upsert_item(user_data)
    return user_data


@router.post("/resend-confirmation")
async def resend_confirmation_email(req: MagicLinkRequest) -> dict[str, str]:
    """Resend a confirmation email and report actual provider failures to the UI."""
    try:
        await _send_confirmation_email(str(req.email), req.first_name or "Bonde", is_resend=True)
    except EmailDeliveryError as exc:
        logger.warning("Confirmation resend failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return {"status": "ok", "message": "Bekreftelses-e-post er sendt på nytt."}


@router.post("/register")
async def register_user(req: RegisterRequest) -> AuthResponse:
    """Persist a complete onboarding profile after password or Google verification."""
    users_container = get_users_container()
    email = str(req.email).lower()
    first_name = req.first_name.strip()
    last_name = req.last_name.strip()
    address = (req.address or "").strip() or None
    onboarding_role = (req.onboarding_role or "").strip() or None
    google_identity: Optional[GoogleIdentityResponse] = None

    if req.google_token:
        try:
            google_identity = _google_identity_from_payload(await verify_google_token(req.google_token))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        email = google_identity.email
        first_name = google_identity.first_name
        last_name = google_identity.last_name

    try:
        existing_by_google_id = (
            _find_user(users_container, "google_id", google_identity.google_id) if google_identity else None
        )
        existing_by_email = _find_user(users_container, "email", email)
        if existing_by_google_id and existing_by_email and existing_by_google_id["id"] != existing_by_email["id"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Google-kontoen er koblet til en annen Barebonde-bruker.",
            )

        existing = existing_by_google_id or existing_by_email
        if existing and not google_identity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="En bruker med denne e-postadressen finnes allerede.",
            )

        if existing:
            user_data = _upsert_existing_user(
                users_container,
                existing,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=req.phone_number,
                address=address,
                onboarding_role=onboarding_role,
                google_id=google_identity.google_id if google_identity else None,
                picture=google_identity.picture if google_identity else None,
            )
        else:
            user = User(
                email=email,
                better_auth_id=f"google_{google_identity.google_id}" if google_identity else f"user_{email}",
                first_name=first_name,
                last_name=last_name,
                google_id=google_identity.google_id if google_identity else None,
                phone_number=req.phone_number,
                address=address,
                onboarding_role=onboarding_role,
            )
            user_data = user.to_dict()
            if google_identity and google_identity.picture:
                user_data["picture"] = google_identity.picture
            users_container.upsert_item(user_data)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        logger.error("Failed saving onboarding user: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kunne ikke opprette brukeren akkurat nå. Prøv igjen.",
        ) from exc

    if google_identity:
        return AuthResponse(
            user_id=str(user_data["id"]),
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=req.phone_number,
            email_sent=False,
            email_message="E-postadressen er bekreftet av Google.",
            message="Google-kontoen og den personlige profilen er lagret.",
        )

    try:
        await _send_confirmation_email(email, first_name or "Bonde")
    except EmailDeliveryError as exc:
        logger.warning("Registration email was not sent: %s", exc)
        return AuthResponse(
            user_id=str(user_data["id"]),
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=req.phone_number,
            email_sent=False,
            email_message=str(exc),
            message="Kontoen er opprettet, men bekreftelses-e-posten kunne ikke sendes.",
        )

    return AuthResponse(
        user_id=str(user_data["id"]),
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone_number=req.phone_number,
        email_sent=True,
        email_message="Bekreftelses-e-post er sendt.",
        message="Bruker opprettet. Sjekk e-posten din for videre instruksjoner.",
    )


@router.post("/login")
async def login_user(req: LoginRequest) -> AuthResponse:
    """Authenticate an existing user in the current demo-mode flow."""
    users_container = get_users_container()
    email = str(req.email).lower()
    query = f"SELECT * FROM c WHERE c.email = '{email}'"
    users = list(users_container.query_items(query=query, enable_cross_partition_query=True))

    if not users:
        return AuthResponse(
            user_id="demo-user-id",
            email=email,
            first_name="Bonde",
            last_name="Bruker",
            message="Innlogget i demo-modus",
        )

    user_data = users[0]
    return AuthResponse(
        user_id=user_data.get("id", "demo-id"),
        email=user_data.get("email", email),
        first_name=user_data.get("first_name", "Bonde"),
        last_name=user_data.get("last_name", ""),
        message="Vellykket innlogging",
    )


@router.post("/magic-link")
async def send_magic_link(req: MagicLinkRequest) -> dict[str, str]:
    """Send a magic-link style dashboard email through the same Plunk sender."""
    try:
        await _send_plunk_email(
            to=str(req.email),
            subject="Din innloggingslenke til Barebonde",
            body=(
                f"<h1>Logg inn på Barebonde</h1>"
                f"<p><a href='{_frontend_url()}/dashboard'>Åpne dashboardet</a></p>"
            ),
        )
    except EmailDeliveryError as exc:
        logger.warning("Magic-link email was not sent: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return {"status": "ok", "message": "Innloggingslenke sendt på e-post."}


def _get_google_client_id() -> str:
    return (os.getenv("GOOGLE_CLIENT_ID") or "").strip()


@router.get("/google/config", response_model=GoogleConfigResponse)
async def google_config() -> GoogleConfigResponse:
    """Expose the public Google client ID at runtime for the static frontend."""
    client_id = _get_google_client_id()
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google innlogging er ikke konfigurert på serveren.",
        )
    return GoogleConfigResponse(client_id=client_id)


async def verify_google_token(token: str) -> dict[str, Any]:
    """Verify a Google Identity Services credential against the configured audience."""
    google_client_id = _get_google_client_id()
    if not google_client_id:
        raise ValueError("Google OAuth er ikke konfigurert på serveren.")

    try:
        return id_token.verify_oauth2_token(token, requests.Request(), audience=google_client_id)
    except Exception as exc:
        logger.warning("Google token verification failed: %s", exc)
        raise ValueError("Google-tokenet er ugyldig eller utløpt.") from exc


@router.post("/google", response_model=GoogleAuthResponse)
async def google_auth(req: GoogleTokenRequest) -> GoogleAuthResponse:
    """Verify Google login for an existing, completed Barebonde profile."""
    if not req.token or not req.token.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token er påkrevd.")

    try:
        payload = await verify_google_token(req.token)
        identity = _google_identity_from_payload(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    try:
        users_container = get_users_container()
        existing_by_google_id = _find_user(users_container, "google_id", identity.google_id)
        existing_by_email = _find_user(users_container, "email", identity.email)
        if existing_by_google_id and existing_by_email and existing_by_google_id["id"] != existing_by_email["id"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Google-kontoen er koblet til en annen Barebonde-bruker.",
            )
        existing = existing_by_google_id or existing_by_email
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Finner ikke en fullført Barebonde-konto. Fullfør gårdsoppsettet før du logger inn med Google.",
            )

        user_data = _upsert_existing_user(
            users_container,
            existing,
            email=identity.email,
            first_name=identity.first_name,
            last_name=identity.last_name,
            google_id=identity.google_id,
            picture=identity.picture,
        )
        user_id = str(user_data["id"])
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        logger.error("Could not persist Google user: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google-innlogging lyktes, men brukeren kunne ikke lagres. Prøv igjen.",
        ) from exc

    return GoogleAuthResponse(
        user_id=user_id,
        email=identity.email,
        first_name=identity.first_name,
        last_name=identity.last_name,
        picture=identity.picture,
        message="Innlogget med Google.",
    )


@router.post("/google/verify", response_model=GoogleIdentityResponse)
async def verify_google_identity(req: GoogleTokenRequest) -> GoogleIdentityResponse:
    """Verify Google claims without creating a Cosmos profile before onboarding completes."""
    if not req.token or not req.token.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token er påkrevd.")

    try:
        return _google_identity_from_payload(await verify_google_token(req.token))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
