"""
Pydantic schemas for authentication
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserResponse(BaseModel):
    """User response model"""
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response after authentication"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: UserResponse


class LoginCallbackRequest(BaseModel):
    """ID-porten login callback request"""
    code: str
    state: Optional[str] = None


class TokenPayload(BaseModel):
    """JWT token payload"""
    sub: int  # user_id
    email: str
    exp: datetime
    iat: datetime
