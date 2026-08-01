"""
Farm management routes using Cosmos DB (Open Demo Mode)
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from azure.cosmos import exceptions
import logging

from app.db.cosmos_client import get_farms_container, get_farm_users_container
from app.db.cosmos_models import Farm, FarmUser, UserRole

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
async def create_farm(request: FarmCreateRequest) -> FarmResponse:
    """
    Create a new farm (Demo Mode)
    """
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
                detail="Dette organisasjonsnummeret er allerede registrert"
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
        logger.info(f"Created farm in demo mode: {farm.id} - {request.name}")
        
        # Link demo user as owner
        farm_users_container = get_farm_users_container()
        farm_user = FarmUser(
            user_id="demo-user",
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
async def get_farm(farm_id: str) -> FarmResponse:
    """
    Get farm details (Demo Mode)
    """
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
