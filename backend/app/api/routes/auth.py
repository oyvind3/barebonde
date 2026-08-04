"""User authentication, onboarding, Plunk email, and Google OAuth routes."""

from __future__ import annotations

import html
import logging
import os
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token
from pydantic import BaseModel, EmailStr

from app.db.cosmos_client import get_users_container
from app.db.cosmos_models import User

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_PLUNK_API_URL = "https://next-api.useplunk.com/v1/send"
DEFAULT_FRONTEND_URL = "https://salmon-ocean-076260203.7.azurestaticapps.net"


class EmailDeliveryError(Exception):
    """Raised when a transactional email cannot be submitted to Plunk."""


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    address: Optional[str] = None
    farm_name: Optional[str] = None
    org_number: Optional[str] = None


class AuthResponse(BaseModel):
    user_id: str
    email: str
    first_name: str
    last_name: str
    message: str
    email_sent: bool = False
    email_message: Optional[str] = None


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
    """Create a Cosmos user and submit an email confirmation through Plunk."""
    users_container = get_users_container()
    email = str(req.email).lower()
    query = f"SELECT * FROM c WHERE c.email = '{email}'"
    existing = list(users_container.query_items(query=query, enable_cross_partition_query=True))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="En bruker med denne e-postadressen finnes allerede.",
        )

    user = User(
        email=email,
        better_auth_id=f"user_{email}",
        first_name=req.first_name.strip(),
        last_name=req.last_name.strip(),
    )
    try:
        users_container.upsert_item(user.to_dict())
    except Exception as exc:
        logger.error("Failed saving onboarding user: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kunne ikke opprette brukeren akkurat nå. Prøv igjen.",
        ) from exc

    try:
        await _send_confirmation_email(email, user.first_name or "Bonde")
    except EmailDeliveryError as exc:
        logger.warning("Registration email was not sent: %s", exc)
        return AuthResponse(
            user_id=user.id,
            email=user.email,
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            email_sent=False,
            email_message=str(exc),
            message="Kontoen er opprettet, men bekreftelses-e-posten kunne ikke sendes.",
        )

    return AuthResponse(
        user_id=user.id,
        email=user.email,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
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
    """Verify a Google credential and create or update the Cosmos user document."""
    if not req.token or not req.token.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token er påkrevd.")

    try:
        payload = await verify_google_token(req.token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    google_id = str(payload.get("sub") or "")
    email = str(payload.get("email") or "").lower()
    first_name = str(payload.get("given_name") or payload.get("name") or "Bonde")
    last_name = str(payload.get("family_name") or "")
    picture = payload.get("picture")
    if not google_id or not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google-tokenet mangler brukeridentitet.")

    try:
        users_container = get_users_container()
        query = f"SELECT * FROM c WHERE c.email = '{email}'"
        existing = list(users_container.query_items(query=query, enable_cross_partition_query=True))
        if existing:
            user_data = existing[0]
            user_data.update(
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "picture": picture,
                    "google_id": google_id,
                }
            )
            users_container.upsert_item(user_data)
            user_id = str(user_data["id"])
        else:
            user = User(
                email=email,
                better_auth_id=f"google_{google_id}",
                first_name=first_name,
                last_name=last_name,
                google_id=google_id,
            )
            user_data = user.to_dict()
            if picture:
                user_data["picture"] = picture
            users_container.upsert_item(user_data)
            user_id = user.id
    except Exception as exc:
        logger.error("Could not persist Google user: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google-innlogging lyktes, men brukeren kunne ikke lagres. Prøv igjen.",
        ) from exc

    return GoogleAuthResponse(
        user_id=user_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        picture=str(picture) if picture else None,
        message="Innlogget med Google.",
    )
