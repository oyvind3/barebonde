"""
Authentication routes using better-auth.com
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import User
from app.core.security import get_current_user
from app.services.better_auth_service import better_auth_service
from app.schemas.auth import UserResponse

router = APIRouter()


class CallbackRequest(BaseModel):
    """Request body for auth callback"""
    code: str
    session_token: Optional[str] = None


class VerifyResponse(BaseModel):
    """Response for session verification"""
    user: UserResponse
    session_valid: bool


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
async def auth_callback(
    request: CallbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle auth callback from better-auth.com
    
    The frontend will send the session token returned from better-auth.com
    We verify it and create/sync the local user entry
    
    Args:
        request: Contains session token from better-auth.com
        db: Database session
    
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
    
    # Create or get local user
    user = await better_auth_service.create_or_get_user_local(db, user_details)
    
    # Fetch user's organizations and sync to local farm_users
    organizations = await better_auth_service.get_organizations(better_auth_user_id)
    if organizations:
        await better_auth_service.sync_farm_membership(db, user, organizations)
    
    await db.commit()
    
    return {
        "user": UserResponse.from_orm(user),
        "session_token": request.session_token,
        "token_type": "bearer"
    }


@router.post("/verify")
async def verify_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify current session and return user info
    
    Args:
        current_user: Current authenticated user from session verification
        db: Database session
    
    Returns:
        User details if session is valid
    """
    return {
        "user": UserResponse.from_orm(current_user),
        "session_valid": True
    }


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Logout the current user
    
    Note: The actual session invalidation happens on the frontend
    by clearing the session token. This endpoint is mainly for
    backend cleanup if needed.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Success message
    """
    # Clear session cache for this user
    from app.core.security import clear_session_cache
    clear_session_cache()
    
    return {"message": "Successfully logged out"}
    Refresh access token using refresh token
    """
    try:
        user, new_access_token = await auth_service.refresh_access_token(
            db, refresh_token
        )
        
        return TokenResponse(
            access_token=new_access_token,
            token_type="bearer",
            user=UserResponse.from_orm(user)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token refresh failed: {str(e)}"
        )


@router.post("/logout")
async def logout(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke refresh token (logout)
    """
    await auth_service.revoke_refresh_token(db, refresh_token)
    return {"message": "Logged out successfully"}
