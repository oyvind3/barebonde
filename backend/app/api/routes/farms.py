"""
Farm management routes using Cosmos DB (Open Demo Mode)
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel
from azure.cosmos import exceptions
import logging

from app.db.cosmos_client import get_farms_container, get_farm_users_container
from app.db.cosmos_models import Farm, FarmUser, UserRole
from app.services.brreg_service import brreg_service

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
    brreg_verified: bool = False


class BrregLookupResponse(BaseModel):
    """Response for BRREG lookup."""
    org_number: str
    name: str
    organization_form: str
    postal_code: str
    city: str
    municipality: str
    address: str
    is_active: bool = True
    registered_mva: str = "Ukjent"
    industry_code: str = ""
    registered_date: str = ""


@router.get("/search")
async def search_companies(q: str) -> list[BrregLookupResponse]:
    """
    Search BRREG for companies by name or 9-digit org number.
    """
    query_str = q.strip()
    if not query_str or len(query_str) < 2:
        return []

    try:
        results = await brreg_service.search_orgs(query_str, size=10)
        return [BrregLookupResponse(**item) for item in results]
    except Exception as exc:
        logger.error(f"BRREG search failed for query '{q}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Klarte ikke hente data fra Brønnøysund akkurat nå. Prøv igjen."
        ) from exc


@router.get("/lookup/{org_number}")
async def lookup_org_number(org_number: str) -> BrregLookupResponse:
    """
    Look up organization details from BRREG using organization number.
    """
    try:
        result = await brreg_service.lookup_org(org_number)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.error(f"BRREG lookup failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Klarte ikke hente data fra Brønnøysund akkurat nå. Prøv igjen."
        ) from exc

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fant ikke organisasjonsnummeret i Brønnøysundregisteret"
        )

    return BrregLookupResponse(**result)


@router.post("")
async def create_farm(
    request: FarmCreateRequest,
    x_onboarding_user_id: Optional[str] = Header(default=None)
) -> FarmResponse:
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
    
    brreg_data = None
    try:
        brreg_data = await brreg_service.lookup_org(request.org_number)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.warning(f"Skipping BRREG enrich due to transient error: {exc}")

    if not brreg_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organisasjonsnummeret finnes ikke i Brønnøysundregisteret"
        )

    try:
        # Create farm
        farm = Farm(
            name=request.name.strip() or brreg_data.get("name", ""),
            org_number=request.org_number,
            address=request.address or brreg_data.get("address", ""),
            municipality=request.municipality or brreg_data.get("municipality", ""),
            brreg_verified=True
        )
        
        # Save to Cosmos DB
        farms_container.upsert_item(farm.to_dict())
        logger.info(f"Created farm in demo mode: {farm.id} - {request.name}")
        
        # Link onboarding user as owner (prepares for full auth integration).
        user_id = (x_onboarding_user_id or "demo-user").strip() or "demo-user"
        farm_users_container = get_farm_users_container()
        farm_user = FarmUser(
            user_id=user_id,
            farm_id=farm.id,
            role=UserRole.OWNER
        )
        farm_users_container.upsert_item(farm_user.to_dict())
        
        return FarmResponse(
            id=farm.id,
            name=farm.name,
            org_number=farm.org_number,
            address=farm.address,
            municipality=farm.municipality,
            brreg_verified=farm.brreg_verified
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
            municipality=farm.municipality,
            brreg_verified=farm.brreg_verified
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
