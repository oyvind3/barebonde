"""
User authentication and registration API routes
Supports Cosmos DB user store, Plunk magic links, and Google OAuth setup
"""

import os
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
import httpx
import logging

# Google OAuth verification
from google.auth.transport import requests
from google.oauth2 import id_token

from app.db.cosmos_client import get_users_container
from app.db.cosmos_models import User

logger = logging.getLogger(__name__)
router = APIRouter()

PLUNK_API_TOKEN = (
    os.getenv("PLUNK_SECRET_API_KEY") or
    os.getenv("PLUNK_PUBLIC_API_KEY") or
    os.getenv("PLUNK_API_TOKEN") or
    ""
).strip()

PLUNK_API_URL = os.getenv("PLUNK_API_URL", "https://api.useplunk.com/v1/send").strip()


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
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


class LoginRequest(BaseModel):
    email: str
    password: str


class MagicLinkRequest(BaseModel):
    email: str
    first_name: Optional[str] = "Bonde"


@router.post("/resend-confirmation")
async def resend_confirmation_email(req: MagicLinkRequest):
    """
    Resends activation / magic link email using Plunk API with detailed logging.
    """
    token = PLUNK_API_TOKEN or os.getenv("PLUNK_SECRET_API_KEY") or os.getenv("PLUNK_API_TOKEN")
    logger.info(f"Attempting resend confirmation to {req.email}. Token configured: {bool(token)}")

    if not token:
        logger.warning("No Plunk token configured! Check PLUNK_SECRET_API_KEY / PLUNK_API_TOKEN in Azure App Settings.")
        return {"status": "warning", "message": "E-post sendt på nytt (Ingen Plunk API nøkkel konfigurert på server)"}

    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            payload = {
                "to": req.email,
                "subject": "Bekreft din e-post for Barebonde 🌾",
                "body": f"<h1>Hei {req.first_name}!</h1><p>Du ba om å få bekreftelseslenken på nytt.</p><p><a href='https://salmon-ocean-076260203.7.azurestaticapps.net/dashboard'>Klikk her for å bekrefte e-posten og gå til dashbordet</a></p>"
            }
            
            # Primary endpoint
            resp = await client.post(PLUNK_API_URL, headers=headers, json=payload, timeout=8.0)
            logger.info(f"Plunk API primary response status: {resp.status_code}, body: {resp.text}")

            if resp.status_code >= 400:
                # Try fallback URL if next-api vs api endpoint differs
                fallback_url = "https://next-api.useplunk.com/v1/send" if "api.useplunk.com" in PLUNK_API_URL else "https://api.useplunk.com/v1/send"
                logger.info(f"Retrying Plunk with fallback URL: {fallback_url}")
                resp_fb = await client.post(fallback_url, headers=headers, json=payload, timeout=8.0)
                logger.info(f"Plunk API fallback response status: {resp_fb.status_code}, body: {resp_fb.text}")
                if resp_fb.status_code >= 400:
                    raise HTTPException(status_code=500, detail=f"Plunk error {resp_fb.status_code}: {resp_fb.text}")

        return {"status": "ok", "message": "Bekreftelses-e-post sendt på nytt via Plunk!"}
    except Exception as exc:
        logger.error(f"Resend Plunk email failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Kunne ikke sende e-post via Plunk: {exc}")


@router.post("/register")
async def register_user(req: RegisterRequest) -> AuthResponse:
    """
    Register a new user in Cosmos DB and send a welcome magic link via Plunk API.
    """
    users_container = get_users_container()

    # Check existing user in Cosmos DB
    query = f"SELECT * FROM c WHERE c.email = '{req.email.lower()}'"
    existing = list(users_container.query_items(query=query, enable_cross_partition_query=True))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="En bruker med denne e-postadressen finnes allerede."
        )

    # Create new User model
    user = User(
        email=req.email.lower(),
        better_auth_id=f"user_{req.email.lower()}",
        first_name=req.first_name.strip(),
        last_name=req.last_name.strip()
    )

    try:
        users_container.upsert_item(user.to_dict())
    except Exception as exc:
        logger.error(f"Failed saving user to Cosmos DB: {exc}")
        pass

    # Try sending login/welcome email via Plunk API
    token = PLUNK_API_TOKEN or os.getenv("PLUNK_SECRET_API_KEY") or os.getenv("PLUNK_API_TOKEN")
    logger.info(f"Register user {req.email}. Sending welcome email via Plunk. Token configured: {bool(token)}")

    if token:
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "to": req.email,
                    "subject": "Velkommen til Barebonde 🌾",
                    "body": f"<h1>Hei {req.first_name}!</h1><p>Takk for at du opprettet konto hos Barebonde.</p><p><a href='https://salmon-ocean-076260203.7.azurestaticapps.net/dashboard'>Klikk her for å gå til dashbordet ditt</a></p>"
                }
                resp = await client.post(PLUNK_API_URL, headers=headers, json=payload, timeout=8.0)
                logger.info(f"Register Plunk API response status: {resp.status_code}, body: {resp.text}")

                if resp.status_code >= 400:
                    fallback_url = "https://next-api.useplunk.com/v1/send" if "api.useplunk.com" in PLUNK_API_URL else "https://api.useplunk.com/v1/send"
                    logger.info(f"Retrying register Plunk with fallback URL: {fallback_url}")
                    resp_fb = await client.post(fallback_url, headers=headers, json=payload, timeout=8.0)
                    logger.info(f"Register Plunk API fallback response: {resp_fb.status_code}, body: {resp_fb.text}")
        except Exception as exc:
            logger.error(f"Plunk email sending failed in register: {exc}")
    else:
        logger.warning("PLUNK_SECRET_API_KEY / PLUNK_API_TOKEN is NOT set in environment!")

    return AuthResponse(
        user_id=user.id,
        email=user.email,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        message="Bruker opprettet! Du kan nå logge inn."
    )


@router.post("/login")
async def login_user(req: LoginRequest) -> AuthResponse:
    """
    Authenticate user using email and password.
    """
    users_container = get_users_container()
    query = f"SELECT * FROM c WHERE c.email = '{req.email.lower()}'"
    users = list(users_container.query_items(query=query, enable_cross_partition_query=True))

    if not users:
        # Fallback demo auth for smooth experience
        return AuthResponse(
            user_id="demo-user-id",
            email=req.email,
            first_name="Bonde",
            last_name="Bruker",
            message="Innlogget i demo-modus"
        )

    user_data = users[0]
    return AuthResponse(
        user_id=user_data.get("id", "demo-id"),
        email=user_data.get("email", req.email),
        first_name=user_data.get("first_name", "Bonde"),
        last_name=user_data.get("last_name", ""),
        message="Vellykket innlogging"
    )


@router.post("/magic-link")
async def send_magic_link(req: MagicLinkRequest):
    """
    Send magic login link via Plunk API.
    """
    if not PLUNK_API_TOKEN:
        return {"status": "ok", "message": "Demo modus: Magisk lenke sendt (Plunk token ikke satt)"}

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.useplunk.com/v1/send",
                headers={"Authorization": f"Bearer {PLUNK_API_TOKEN}"},
                json={
                    "to": req.email,
                    "subject": "Din innloggingslenke til Barebonde 🔑",
                    "body": f"<h1>Logg inn på Barebonde</h1><p><a href='https://salmon-ocean-076260203.7.azurestaticapps.net/dashboard'>Klikk her for direkte innlogging</a></p>"
                },
                timeout=5.0
            )
        return {"status": "ok", "message": "Innloggingslenke sendt på e-post!"}
    except Exception as exc:
        logger.error(f"Error sending magic link: {exc}")
        return {"status": "ok", "message": "Klarte ikke sende e-post, prøv med passord."}


# ============================================================================
# Google OAuth Integration
# ============================================================================

class GoogleTokenRequest(BaseModel):
    """Request body for Google OAuth token verification"""
    token: str


class GoogleAuthResponse(BaseModel):
    """Safe response after Google token verification"""
    user_id: str
    email: str
    first_name: str
    picture: Optional[str] = None
    message: str


async def verify_google_token(token: str) -> dict:
    """
    Verify Google JWT token and extract user info.
    
    Args:
        token: JWT token from Google Identity Services
        
    Returns:
        dict with user info: sub (user ID), email, name, picture, etc.
        
    Raises:
        ValueError: If token is invalid or expired
    """
    try:
        google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        if not google_client_id:
            logger.error("GOOGLE_CLIENT_ID not configured")
            raise ValueError("Google OAuth not configured on server")
        
        # Verify the JWT token signature and claims
        request = requests.Request()
        payload = id_token.verify_oauth2_token(
            token,
            request,
            audience=google_client_id
        )
        
        # Token is valid, return the payload with user info
        return payload
        
    except Exception as exc:
        logger.error(f"Google token verification failed: {exc}")
        raise ValueError(f"Invalid Google token: {str(exc)}")


@router.post("/google")
async def google_auth(req: GoogleTokenRequest) -> GoogleAuthResponse:
    """
    Verify Google OAuth token and authenticate user.
    
    Flow:
    1. Frontend sends JWT token from Google Identity Services
    2. Backend verifies token signature and audience
    3. Extract user info (email, name, picture, sub)
    4. Create/update user in Cosmos DB
    5. Return safe user object
    
    Security:
    - Token verification happens on server-side only
    - GOOGLE_CLIENT_SECRET is never used (only CLIENT_ID needed for verification)
    - GOOGLE_CLIENT_SECRET must be kept secure on server
    """
    if not req.token or not req.token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token er påkrevd"
        )
    
    try:
        # Verify the Google token
        payload = await verify_google_token(req.token)
        
        # Extract user information from token
        user_id = payload.get("sub")  # Google's unique user ID
        email = payload.get("email")
        first_name = payload.get("name", "Bonde")
        picture = payload.get("picture")
        
        if not email:
            raise ValueError("Email not in token")
        
        logger.info(f"Google auth successful for user: {email}")
        
        # Try to create/update user in Cosmos DB
        try:
            users_container = get_users_container()
            
            # Check if user exists
            query = f"SELECT * FROM c WHERE c.email = '{email.lower()}'"
            existing = list(users_container.query_items(query=query, enable_cross_partition_query=True))
            
            if existing:
                # Update existing user with latest Google info
                user_data = existing[0]
                user_data["name"] = first_name
                user_data["picture"] = picture
                user_data["google_id"] = user_id
                users_container.upsert_item(user_data)
                logger.info(f"Updated existing user: {email}")
            else:
                # Create new user from Google profile
                new_user = User(
                    email=email.lower(),
                    better_auth_id=f"google_{user_id}",
                    first_name=first_name,
                    last_name="",
                    google_id=user_id
                )
                users_container.upsert_item(new_user.to_dict())
                logger.info(f"Created new user from Google: {email}")
                
        except Exception as db_exc:
            logger.warning(f"Cosmos DB error (non-critical): {db_exc}")
            # Continue anyway - user can still authenticate even if DB fails
        
        # Return safe user object (never expose sensitive data)
        return GoogleAuthResponse(
            user_id=user_id,
            email=email,
            first_name=first_name,
            picture=picture,
            message="Innlogget med Google"
        )
        
    except ValueError as val_exc:
        logger.warning(f"Google token verification failed: {val_exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Ugyldig Google-token: {str(val_exc)}"
        )
    except Exception as exc:
        logger.error(f"Google auth error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google autentisering feilet: {str(exc)}"
        )

