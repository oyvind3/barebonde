"""Small response models shared by the Identity HTTP routes."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class IdentityUserResponse(BaseModel):
    user_id: str
    email: str
    first_name: str
    last_name: str = ""
    picture: Optional[str] = None
    phone_number: Optional[str] = None
    status: str


class SessionResponse(BaseModel):
    session_id: str
    created_at: str
    last_seen_at: Optional[str] = None
    expires_at: str
    current: bool = True


class AuthenticatedResponse(IdentityUserResponse):
    session: SessionResponse
    csrf_token: str
    message: str


class MeResponse(BaseModel):
    user: IdentityUserResponse
    session: SessionResponse
    csrf_token: str


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
