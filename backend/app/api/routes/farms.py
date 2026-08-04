"""
Farm management routes using Cosmos DB (Open Demo Mode)
"""

from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel, EmailStr, Field, field_validator
from azure.cosmos import exceptions
import logging

from app.db.cosmos_client import get_farms_container, get_farm_users_container
from app.db.cosmos_models import Farm, FarmUser, UserRole
from app.services.brreg_service import brreg_service

logger = logging.getLogger(__name__)
router = APIRouter()

FARM_TYPES = {"plante", "husdyr", "skog", "blandet", "annet"}
PRODUCTION_TYPES = {
    "korn", "grovfor", "melk", "storfe", "sau_geit", "svin", "fjorkre_egg",
    "frukt_baer", "gronnsaker_potet", "skogbruk", "annen_produksjon",
}
FARM_SIZE_RANGES = {"under_50", "50_199", "200_499", "500_plus", "vet_ikke"}
TEAM_SIZES = {"1", "2_5", "6_10", "11_plus"}
ONBOARDING_GOALS = {"regnskap", "bilag", "dokumenter", "frister", "maskiner", "areal", "driftsplan", "integrasjoner"}
BILLING_METHODS = {"faktura", "vipps"}


class FarmCreateRequest(BaseModel):
    """Request body for creating a farm"""
    name: str
    org_number: str
    address: Optional[str] = None
    municipality: Optional[str] = None
    manual_entry: bool = False
    organization_form: Optional[str] = None
    industry_code: Optional[str] = None
    primary_farm_type: Optional[str] = None
    production_types: list[str] = Field(default_factory=list)
    farm_size_range: Optional[str] = None
    team_size: Optional[str] = None
    onboarding_goals: list[str] = Field(default_factory=list)
    billing_method: Optional[str] = None
    billing_email: Optional[EmailStr] = None

    @field_validator("primary_farm_type")
    @classmethod
    def validate_primary_farm_type(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in FARM_TYPES:
            raise ValueError("Ukjent driftsretning.")
        return value

    @field_validator("farm_size_range")
    @classmethod
    def validate_farm_size_range(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in FARM_SIZE_RANGES:
            raise ValueError("Ukjent størrelsesintervall.")
        return value

    @field_validator("team_size")
    @classmethod
    def validate_team_size(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in TEAM_SIZES:
            raise ValueError("Ukjent teamstørrelse.")
        return value

    @field_validator("billing_method")
    @classmethod
    def validate_billing_method(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in BILLING_METHODS:
            raise ValueError("Ukjent betalingsmetode.")
        return value

    @field_validator("production_types", "onboarding_goals")
    @classmethod
    def validate_list_values(cls, value: list[str], info) -> list[str]:
        allowed_values = PRODUCTION_TYPES if info.field_name == "production_types" else ONBOARDING_GOALS
        if any(item not in allowed_values for item in value):
            raise ValueError("Valget inneholder en ukjent onboardingverdi.")
        return list(dict.fromkeys(value))


class FarmResponse(BaseModel):
    """Response model for farm"""
    id: str
    name: str
    org_number: str
    address: Optional[str]
    municipality: Optional[str]
    brreg_verified: bool = False
    organization_form: str = ""
    industry_code: str = ""
    primary_farm_type: str = ""
    production_types: list[str] = Field(default_factory=list)
    farm_size_range: str = ""
    team_size: str = ""
    onboarding_goals: list[str] = Field(default_factory=list)
    billing_method: str = ""
    billing_email: str = ""


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
    requested_org_number = request.org_number.strip()
    is_manual_without_org_number = request.manual_entry and (
        not requested_org_number.isdigit() or len(requested_org_number) != 9 or requested_org_number == "000000000"
    )
    org_number = f"manual-{uuid4()}" if is_manual_without_org_number else requested_org_number
    try:
        query = "SELECT * FROM farms f WHERE f.org_number = @org_number"
        items = list(farms_container.query_items(
            query=query,
            parameters=[{"name": "@org_number", "value": org_number}],
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
    if not is_manual_without_org_number:
        try:
            brreg_data = await brreg_service.lookup_org(org_number)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc)
            ) from exc
        except Exception as exc:
            logger.warning(f"Skipping BRREG enrich due to transient error: {exc}")

    if not brreg_data and not request.manual_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organisasjonsnummeret finnes ikke i Brønnøysundregisteret"
        )

    try:
        # Create farm
        farm = Farm(
            name=request.name.strip() or (brreg_data or {}).get("name", ""),
            org_number=org_number,
            address=request.address or (brreg_data or {}).get("address", ""),
            municipality=request.municipality or (brreg_data or {}).get("municipality", ""),
            brreg_verified=bool(brreg_data),
            organization_form=request.organization_form or (brreg_data or {}).get("organization_form", ""),
            industry_code=request.industry_code or (brreg_data or {}).get("industry_code", ""),
            primary_farm_type=request.primary_farm_type,
            production_types=request.production_types,
            farm_size_range=request.farm_size_range,
            team_size=request.team_size,
            onboarding_goals=request.onboarding_goals,
            billing_method=request.billing_method,
            billing_email=str(request.billing_email or ""),
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
            brreg_verified=farm.brreg_verified,
            organization_form=farm.organization_form,
            industry_code=farm.industry_code,
            primary_farm_type=farm.primary_farm_type,
            production_types=farm.production_types,
            farm_size_range=farm.farm_size_range,
            team_size=farm.team_size,
            onboarding_goals=farm.onboarding_goals,
            billing_method=farm.billing_method,
            billing_email=farm.billing_email,
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
            brreg_verified=farm.brreg_verified,
            organization_form=farm.organization_form,
            industry_code=farm.industry_code,
            primary_farm_type=farm.primary_farm_type,
            production_types=farm.production_types,
            farm_size_range=farm.farm_size_range,
            team_size=farm.team_size,
            onboarding_goals=farm.onboarding_goals,
            billing_method=farm.billing_method,
            billing_email=farm.billing_email,
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
