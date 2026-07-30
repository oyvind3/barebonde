"""
Farm management routes
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import User, Farm, FarmUser, UserRole
from app.core.security import get_current_user, verify_farm_owner

router = APIRouter()


class FarmCreateRequest(BaseModel):
    """Request body for creating a farm"""
    name: str
    org_number: str
    address: Optional[str] = None
    municipality: Optional[str] = None


class FarmResponse(BaseModel):
    """Response model for farm"""
    id: int
    name: str
    org_number: str
    address: Optional[str]
    municipality: Optional[str]
    
    class Config:
        from_attributes = True


@router.post("")
async def create_farm(
    request: FarmCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FarmResponse:
    """
    Create a new farm
    
    The authenticated user becomes the owner of the farm.
    In production, also creates an organization in better-auth.com.
    
    Args:
        request: Farm creation details
        current_user: Authenticated user
        db: Database session
    
    Returns:
        Created farm details
    
    Raises:
        HTTPException: If org_number already exists or invalid
    """
    # Validate org_number doesn't already exist
    stmt = select(Farm).where(Farm.org_number == request.org_number)
    existing_farm = await db.scalar(stmt)
    
    if existing_farm:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Denne organisasjonsnummeret er allerede registrert"
        )
    
    try:
        # Create farm
        farm = Farm(
            name=request.name,
            org_number=request.org_number,
            address=request.address or "",
            municipality=request.municipality or ""
        )
        db.add(farm)
        await db.flush()
        
        # Add current user as owner
        farm_user = FarmUser(
            user_id=current_user.id,
            farm_id=farm.id,
            role=UserRole.OWNER
        )
        db.add(farm_user)
        
        # TODO: Create organization in better-auth.com
        # from app.services.better_auth_service import better_auth_service
        # org_data = await better_auth_service.create_organization(
        #     current_user.better_auth_id,
        #     name=request.name,
        #     metadata={"org_number": request.org_number, "farm_id": farm.id}
        # )
        
        await db.commit()
        return FarmResponse.from_orm(farm)
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feil ved opprettelse av gård: {str(e)}"
        )


@router.get("/{farm_id}")
async def get_farm(
    farm_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FarmResponse:
    """
    Get farm details (requires access to farm)
    
    Args:
        farm_id: The farm ID
        current_user: Authenticated user
        db: Database session
    
    Returns:
        Farm details
    
    Raises:
        HTTPException: If farm not found or user doesn't have access
    """
    # Verify access
    await verify_farm_owner(farm_id, current_user, db)
    
    stmt = select(Farm).where(Farm.id == farm_id)
    farm = await db.scalar(stmt)
    
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gården ble ikke funnet"
        )
    
    return FarmResponse.from_orm(farm)
