"""
Authentication routes using better-auth.com with Cosmos DB
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.better_auth_service import better_auth_service
from app.db.cosmos_models import User

router = APIRouter()


class CallbackRequest(BaseModel):
    """Request body for auth callback"""
    code: str
    session_token: Optional[str] = None


@router.get("/login")
async def get_login_url():
    """
    Get the better-auth.com login/signup URL
    
    Returns:
        URL for frontend to redirect user to
    """
    # In a real implementation, this would generate a proper URL
    # For now, return the better-auth.com hosted auth page
    return {
        "login_url": "https://dash.better-auth.com/sign-in",
        "note": "Configure your better-auth.com project URL here"
    }


@router.post("/callback")
async def auth_callback(request: CallbackRequest):
    """
    Handle auth callback from better-auth.com
    
    The frontend will send the session token returned from better-auth.com
    We verify it and create/sync the local user entry
    
    Args:
        request: Contains session token from better-auth.com
    
    Returns:
        User info and session status
    """
    if not request.session_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_token is required"
        )
    
    # Verify session with better-auth.com
    session_data = await better_auth_service.verify_session(request.session_token)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token"
        )
    
    # Get full user details from better-auth.com
    better_auth_user_id = session_data.get("user_id")
    user_details = await better_auth_service.get_user(better_auth_user_id)
    if not user_details:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not retrieve user details"
        )
    
    # Create or get local user from Cosmos DB
    user = await better_auth_service.create_or_get_user_local(user_details)
    
    # Fetch user's organizations and sync to local farm_users
    organizations = await better_auth_service.get_organizations(better_auth_user_id)
    if organizations:
        await better_auth_service.sync_farm_membership(user, organizations)
    
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name
        },
        "session_token": request.session_token,
        "token_type": "bearer"
    }


@router.post("/verify")
async def verify_session(
    authorization: Optional[str] = None
):
    """
    Verify current session and return user info
    
    Args:
        authorization: Bearer token from header
    
    Returns:
        User details if session is valid
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    session_token = authorization.replace("Bearer ", "")
    
    # Verify with better-auth.com
    session_data = await better_auth_service.verify_session(session_token)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )
    
    return {
        "session_valid": True,
        "user_id": session_data.get("user_id")
    }


@router.post("/logout")
async def logout(authorization: Optional[str] = None):
    """
    Logout the current user
    
    Note: The actual session invalidation happens on the frontend
    by clearing the session token.
    
    Returns:
        Success message
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    return {"message": "Successfully logged out"}
