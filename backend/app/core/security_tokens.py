"""Opaque-token helpers for the server-managed Identity MVP.

The values returned to browsers are random, one-time capable bearer secrets.
Cosmos only receives a keyed digest, so a database export cannot be replayed as
an authenticated browser cookie.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from app.core.config import settings


class IdentitySecurityConfigurationError(RuntimeError):
    """Raised when a request needs the dedicated Identity signing secret."""


def _identity_hmac_key() -> bytes:
    key = settings.identity_hmac_key.strip()
    if not key:
        raise IdentitySecurityConfigurationError(
            "IDENTITY_HMAC_KEY mangler. Serverstyrte sesjoner kan ikke brukes før den er satt."
        )
    return key.encode("utf-8")


def hmac_identifier(namespace: str, value: str) -> str:
    """Create a deterministic, opaque identifier in a purpose-bound namespace."""
    message = f"barebonde:{namespace}:{value}".encode("utf-8")
    return hmac.new(_identity_hmac_key(), message, hashlib.sha256).hexdigest()


def new_opaque_token() -> str:
    """Return a browser-safe random bearer secret; never persist this value."""
    return secrets.token_urlsafe(48)


def verify_hmac_value(expected: str, supplied: str | None) -> bool:
    """Compare a public CSRF value in constant time."""
    return bool(supplied) and hmac.compare_digest(expected, supplied)


def session_identifier(raw_session_token: str) -> str:
    return hmac_identifier("session", raw_session_token)


def challenge_identifier(raw_challenge_token: str) -> str:
    return hmac_identifier("email-login-challenge", raw_challenge_token)


def csrf_token_for_session(raw_session_token: str) -> str:
    return hmac_identifier("csrf", raw_session_token)


def email_lookup_identifier(normalized_email: str) -> str:
    return hmac_identifier("email", normalized_email)


def google_lookup_identifier(google_subject: str) -> str:
    return hmac_identifier("google-subject", google_subject)
