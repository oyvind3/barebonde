"""
Authentication routes for ID-porten OAuth2 flow
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from app.db.database import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import (
    TokenResponse, 
    UserResponse,
    LoginCallbackRequest,
)


router = APIRouter()
auth_service = AuthService()


@router.get("/login")
async def login():
    """
    Initiate ID-porten login flow
    Returns: URL to redirect user to ID-porten
    """
    login_url = auth_service.get_id_porten_login_url()
    return {"login_url": login_url}


@router.post("/callback")
async def login_callback(
    request: LoginCallbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle ID-porten callback after successful authentication
    
    Args:
        request: Contains authorization code from ID-porten
        db: Database session
    
    Returns:
        Access token, refresh token, and user info
    """
    try:
        # Exchange code for token
        token_response = await auth_service.exchange_code_for_token(request.code)
        
        # Get user info from ID-porten
        user_info = await auth_service.get_user_info(token_response.access_token)
        
        # Create or get user in database
        user = await auth_service.create_or_get_user(db, user_info)
        
        # Generate JWT tokens
        access_token = auth_service.create_access_token(user)
        refresh_token = await auth_service.create_refresh_token(db, user)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponse.from_orm(user)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )


@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
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
