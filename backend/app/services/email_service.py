"""Shared Plunk transactional email service.

Extracted from auth routes so sales-invoice e-mail can reuse the same
provider configuration, error handling, and attachment support.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_PLUNK_API_URL = "https://next-api.useplunk.com/v1/send"


class EmailDeliveryError(Exception):
    """Raised when a transactional email cannot be submitted to Plunk."""


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


async def send_transactional_email(
    *,
    to: str,
    subject: str,
    body: str,
    attachments: Optional[list[dict[str, str]]] = None,
    idempotency_key: Optional[str] = None,
) -> dict[str, Any]:
    """Send one transactional email through Plunk's current public API.

    Args:
        to: Recipient e-mail address.
        subject: E-mail subject line.
        body: HTML body content.
        attachments: List of dicts with 'name' and 'content' (base64-encoded).
        idempotency_key: Optional Idempotency-Key header value.

    Returns:
        The parsed provider response payload (safe subset), or empty dict.

    Raises:
        EmailDeliveryError: If the provider rejects or cannot be reached.
    """
    token, from_email, from_name, reply_to, api_url = _get_plunk_config()
    sender: str | dict[str, str] = {"email": from_email, "name": from_name} if from_name else from_email
    payload: dict[str, Any] = {"to": to, "from": sender, "subject": subject, "body": body}
    if reply_to:
        payload["reply"] = reply_to
    if attachments:
        payload["attachments"] = attachments

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=15.0,
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

    return response_payload if isinstance(response_payload, dict) else {}


def validate_plunk_configured() -> None:
    """Raise EmailDeliveryError early if Plunk is not configured."""
    _get_plunk_config()