"""
Security and permission utilities
Handles session verification and farm access control
"""

from typing import Optional, Tuple
from datetime import datetime, timedelta
import logging
from fastapi import HTTPException, status, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import User, FarmUser
from app.services.better_auth_service import better_auth_service

logger = logging.getLogger(__name__)

# In-memory session cache to reduce API calls
_session_cache: dict[str, Tuple[dict, datetime]] = {}
SESSION_CACHE_TTL = 300  # 5 minutes


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Verify session and return current user
    
    Args:
        authorization: Authorization header (Bearer <token>)
        db: Database session
    
    Returns:
        User object
    
    Raises:
        HTTPException: If session invalid or user not found
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    # Check cache first
    if token in _session_cache:
        cached_session, cached_time = _session_cache[token]
        if datetime.utcnow() - cached_time < timedelta(seconds=SESSION_CACHE_TTL):
            # Cache still valid
            better_auth_id = cached_session.get("user_id")
            stmt = select(User).where(User.better_auth_id == better_auth_id)
            user = await db.scalar(stmt)
            if user:
                return user
    
    # Verify session with better-auth.com
    session_data = await better_auth_service.verify_session(token)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    # Cache the session
    better_auth_id = session_data.get("user_id")
    _session_cache[token] = (session_data, datetime.utcnow())
    
    # Get or create user in local database
    stmt = select(User).where(User.better_auth_id == better_auth_id)
    user = await db.scalar(stmt)
    
    if not user:
        # User doesn't exist locally, create entry
        # Note: In production, better-auth.com should have created user in auth flow
        user = User(
            email=session_data.get("email", ""),
            better_auth_id=better_auth_id,
            first_name=session_data.get("first_name", ""),
            last_name=session_data.get("last_name", ""),
            is_active=True
        )
        db.add(user)
        await db.flush()
    
    return user


async def verify_farm_access(
    farm_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FarmUser:
    """
    Verify that current user has access to the specified farm
    
    Args:
        farm_id: The farm ID to verify access for
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        FarmUser object with role info
    
    Raises:
        HTTPException: If user doesn't have access to farm
    """
    stmt = select(FarmUser).where(
        FarmUser.user_id == current_user.id,
        FarmUser.farm_id == farm_id
    )
    farm_user = await db.scalar(stmt)
    
    if not farm_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this farm"
        )
    
    return farm_user


async def verify_farm_owner(
    farm_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FarmUser:
    """
    Verify that current user is an owner of the farm
    
    Args:
        farm_id: The farm ID to verify ownership for
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        FarmUser object if user is owner
    
    Raises:
        HTTPException: If user is not an owner of the farm
    """
    farm_user = await verify_farm_access(farm_id, current_user, db)
    
    if farm_user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only farm owner can perform this action"
        )
    
    return farm_user


def clear_session_cache():
    """Clear the session cache (useful for testing)"""
    _session_cache.clear()
