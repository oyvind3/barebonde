"""
Farm management routes using Cosmos DB
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel
from azure.cosmos import exceptions
import logging

from app.db.cosmos_client import get_farms_container, get_farm_users_container
from app.db.cosmos_models import Farm, FarmUser, UserRole
from app.services.better_auth_service import better_auth_service

logger = logging.getLogger(__name__)
router = APIRouter()


class FarmCreateRequest(BaseModel):
    """Request body for creating a farm"""
    name: str
    org_number: str
    address: Optional[str] = None
    municipality: Optional[str] = None


class FarmResponse(BaseModel):
    """Response model for farm"""
    id: str
    name: str
    org_number: str
    address: Optional[str]
    municipality: Optional[str]


@router.post("")
async def create_farm(
    request: FarmCreateRequest,
    authorization: Optional[str] = Header(None)
) -> FarmResponse:
    """
    Create a new farm
    
    The authenticated user becomes the owner of the farm.
    
    Args:
        request: Farm creation details
        authorization: Bearer token from header
    
    Returns:
        Created farm details
    
    Raises:
        HTTPException: If org_number already exists or invalid
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    session_token = authorization.replace("Bearer ", "")
    
    # Verify session
    session_data = await better_auth_service.verify_session(session_token)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )
    
    better_auth_user_id = session_data.get("user_id")
    user_details = await better_auth_service.get_user(better_auth_user_id)
    if not user_details:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not retrieve user details"
        )
    
    # Get or create local user
    user = await better_auth_service.create_or_get_user_local(user_details)
    
    # Validate org_number doesn't already exist
    farms_container = get_farms_container()
    try:
        query = f"SELECT * FROM farms f WHERE f.org_number = '{request.org_number}'"
        items = list(farms_container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        
        if items:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Denne organisasjonsnummeret er allerede registrert"
            )
    except exceptions.CosmosHttpResponseError as e:
        logger.error(f"Error checking existing farm: {e}")
    
    try:
        # Create farm
        farm = Farm(
            name=request.name,
            org_number=request.org_number,
            address=request.address,
            municipality=request.municipality
        )
        
        # Save to Cosmos DB
        farms_container.upsert_item(farm.to_dict())
        logger.info(f"Created farm: {farm.id} - {request.name}")
        
        # Add current user as owner
        farm_users_container = get_farm_users_container()
        farm_user = FarmUser(
            user_id=user.id,
            farm_id=farm.id,
            role=UserRole.OWNER
        )
        farm_users_container.upsert_item(farm_user.to_dict())
        
        return FarmResponse(
            id=farm.id,
            name=farm.name,
            org_number=farm.org_number,
            address=farm.address,
            municipality=farm.municipality
        )
    
    except Exception as e:
        logger.error(f"Error creating farm: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feil ved opprettelse av gård: {str(e)}"
        )


@router.get("/{farm_id}")
async def get_farm(
    farm_id: str,
    authorization: Optional[str] = Header(None)
) -> FarmResponse:
    """
    Get farm details (requires access to farm)
    
    Args:
        farm_id: The farm ID
        authorization: Bearer token from header
    
    Returns:
        Farm details
    
    Raises:
        HTTPException: If farm not found or user doesn't have access
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    session_token = authorization.replace("Bearer ", "")
    
    # Verify session
    session_data = await better_auth_service.verify_session(session_token)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )
    
    better_auth_user_id = session_data.get("user_id")
    user_details = await better_auth_service.get_user(better_auth_user_id)
    if not user_details:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not retrieve user details"
        )
    
    # Get or create local user
    user = await better_auth_service.create_or_get_user_local(user_details)
    
    # Verify user has access to farm
    farm_users_container = get_farm_users_container()
    try:
        query = f"SELECT * FROM farm_users fu WHERE fu.user_id = '{user.id}' AND fu.farm_id = '{farm_id}'"
        access_items = list(farm_users_container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        
        if not access_items:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Du har ikke tilgang til denne gården"
            )
    except exceptions.CosmosHttpResponseError as e:
        logger.error(f"Error checking farm access: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Feil ved sjekk av gårdtilgang"
        )
    
    # Get farm
    farms_container = get_farms_container()
    try:
        farm_item = farms_container.read_item(item=farm_id, partition_key="")
        farm = Farm.from_dict(farm_item)
        
        return FarmResponse(
            id=farm.id,
            name=farm.name,
            org_number=farm.org_number,
            address=farm.address,
            municipality=farm.municipality
        )
    except exceptions.CosmosResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gården ble ikke funnet"
        )
    except Exception as e:
        logger.error(f"Error getting farm: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Feil ved henting av gård"
        )
