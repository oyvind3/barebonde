"""Farm tenant routes guarded by the authoritative FarmUser membership."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import NAMESPACE_URL, uuid4, uuid5

from azure.cosmos import exceptions
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.api.dependencies.farm_access import AuthorizedFarm, require_farm_permission
from app.api.dependencies.identity import CurrentIdentity, get_current_identity, require_csrf
from app.core.permissions import Permission
from app.db.cosmos_client import get_audit_logs_container, get_farms_container
from app.db.cosmos_models import Farm
from app.services.brreg_service import brreg_service
from app.services.membership_service import (
    InactiveMembershipError,
    MembershipError,
    MembershipNotFoundError,
    MembershipService,
)

logger = logging.getLogger(__name__)
router = APIRouter()

FARM_TYPES = {"plante", "husdyr", "skog", "blandet", "annet"}
PRODUCTION_TYPES = {
    "korn", "grovfor", "melk", "storfe", "sau_geit", "svin", "fjorkre_egg",
    "frukt_baer", "gronnsaker_potet", "skogbruk", "annen_produksjon",
}
FARM_SIZE_RANGES = {"under_50", "50_199", "200_499", "500_plus", "vet_ikke"}
TEAM_SIZES = {"1", "2_5", "6_10", "11_plus"}
ONBOARDING_GOALS = {
    "regnskap", "bilag", "dokumenter", "frister", "maskiner", "areal", "driftsplan", "integrasjoner"
}
BILLING_METHODS = {"faktura", "vipps"}


class FarmCreateRequest(BaseModel):
    name: str
    org_number: str
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
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
        allowed = PRODUCTION_TYPES if info.field_name == "production_types" else ONBOARDING_GOALS
        if any(item not in allowed for item in value):
            raise ValueError("Valget inneholder en ukjent onboardingverdi.")
        return list(dict.fromkeys(value))


class FarmUpdateRequest(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    municipality: Optional[str] = None
    primary_farm_type: Optional[str] = None
    production_types: Optional[list[str]] = None
    farm_size_range: Optional[str] = None
    team_size: Optional[str] = None
    onboarding_goals: Optional[list[str]] = None
    billing_method: Optional[str] = None
    billing_email: Optional[EmailStr] = None

    @field_validator("primary_farm_type")
    @classmethod
    def validate_primary_farm_type(cls, value: Optional[str]) -> Optional[str]:
        return FarmCreateRequest.validate_primary_farm_type(value)

    @field_validator("farm_size_range")
    @classmethod
    def validate_farm_size_range(cls, value: Optional[str]) -> Optional[str]:
        return FarmCreateRequest.validate_farm_size_range(value)

    @field_validator("team_size")
    @classmethod
    def validate_team_size(cls, value: Optional[str]) -> Optional[str]:
        return FarmCreateRequest.validate_team_size(value)

    @field_validator("billing_method")
    @classmethod
    def validate_billing_method(cls, value: Optional[str]) -> Optional[str]:
        return FarmCreateRequest.validate_billing_method(value)

    @field_validator("production_types", "onboarding_goals")
    @classmethod
    def validate_list_values(cls, value: Optional[list[str]], info) -> Optional[list[str]]:
        if value is None:
            return value
        return FarmCreateRequest.validate_list_values(value, info)


class FarmResponse(BaseModel):
    id: str
    name: str
    org_number: str
    address: Optional[str]
    postal_code: str = ""
    city: str = ""
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
    farm_status: str = "active"


class FarmMemberResponse(BaseModel):
    user_id: str
    farm_role: str
    membership_status: str
    created_at: Optional[str] = None


class BrregLookupResponse(BaseModel):
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


def _farm_response(farm: dict[str, Any]) -> FarmResponse:
    model = Farm.from_dict(farm)
    return FarmResponse(
        id=model.id,
        name=model.name,
        org_number=model.org_number,
        address=model.address,
        postal_code=model.postal_code,
        city=model.city,
        municipality=model.municipality,
        brreg_verified=model.brreg_verified,
        organization_form=model.organization_form,
        industry_code=model.industry_code,
        primary_farm_type=model.primary_farm_type,
        production_types=model.production_types,
        farm_size_range=model.farm_size_range,
        team_size=model.team_size,
        onboarding_goals=model.onboarding_goals,
        billing_method=model.billing_method,
        billing_email=model.billing_email,
        farm_status=model.farm_status,
    )


def _deterministic_farm_id(org_number: str) -> str:
    return f"farm:{org_number}"


def _manual_org_number(user_id: str, idempotency_key: Optional[str]) -> str:
    if idempotency_key:
        token = str(uuid5(NAMESPACE_URL, f"barebonde:manual-farm:{user_id}:{idempotency_key}"))
    else:
        token = str(uuid4())
    return f"manual-{token}"


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gården ble ikke funnet.")


def _write_audit_event(event_type: str, farm_id: str, user_id: str) -> None:
    """Audit failures do not invalidate a completed farm operation."""
    try:
        get_audit_logs_container().create_item(
            {
                "id": str(uuid4()),
                "type": "audit_log",
                "event_type": event_type,
                "farm_id": farm_id,
                "actor_user_id": user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as exc:  # Audit is intentionally best-effort in this MVP.
        logger.warning("Could not persist %s audit event for farm %s: %s", event_type, farm_id, exc)


@router.get("/search")
async def search_companies(q: str) -> list[BrregLookupResponse]:
    """Search the public BRREG source; this is not a tenant data route."""
    query_str = q.strip()
    if not query_str or len(query_str) < 2:
        return []
    try:
        return [BrregLookupResponse(**item) for item in await brreg_service.search_orgs(query_str, size=10)]
    except Exception as exc:
        logger.error("BRREG search failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Klarte ikke hente data fra Brønnøysund akkurat nå. Prøv igjen.",
        ) from exc


@router.get("/lookup/{org_number}")
async def lookup_org_number(org_number: str) -> BrregLookupResponse:
    """Look up public organization details from BRREG."""
    try:
        result = await brreg_service.lookup_org(org_number)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("BRREG lookup failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Klarte ikke hente data fra Brønnøysund akkurat nå. Prøv igjen.",
        ) from exc
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fant ikke organisasjonsnummeret i Brønnøysundregisteret")
    return BrregLookupResponse(**result)


@router.post("", response_model=FarmResponse)
async def create_farm(
    request: FarmCreateRequest,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    current: CurrentIdentity = Depends(require_csrf),
) -> FarmResponse:
    """Provision a tenant then its owner membership in a safe retryable saga."""
    user_id = str(current.user["user_id"])
    requested_org_number = request.org_number.strip()
    manual_without_org = request.manual_entry and (
        not requested_org_number.isdigit() or len(requested_org_number) != 9 or requested_org_number == "000000000"
    )
    if idempotency_key and len(idempotency_key) > 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Idempotency-Key er for lang.")
    org_number = _manual_org_number(user_id, idempotency_key) if manual_without_org else requested_org_number
    service = MembershipService(farms_container=get_farms_container())
    existing = service.get_farm_by_org_number(org_number)

    if existing is not None:
        try:
            membership = service.get_active_membership(farm_id=existing["id"], user_id=user_id)
        except (MembershipNotFoundError, InactiveMembershipError):
            membership = None
        if membership is not None:
            if existing.get("farm_status") == "provisioning":
                existing["farm_status"] = "active"
                existing["updated_at"] = datetime.now(timezone.utc).isoformat()
                service.farms.upsert_item(existing)
            return _farm_response(existing)
        if existing.get("farm_status") == "provisioning" and existing.get("created_by_user_id") == user_id:
            try:
                service.create_owner_membership(farm=existing, user_id=user_id)
                existing["farm_status"] = "active"
                existing["updated_at"] = datetime.now(timezone.utc).isoformat()
                service.farms.upsert_item(existing)
                _write_audit_event("FarmMembershipCreated", existing["id"], user_id)
                return _farm_response(existing)
            except MembershipError as exc:
                logger.error("Farm provisioning retry failed for %s: %s", existing["id"], exc)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Gårdsoppsettet er under behandling. Prøv igjen.",
                ) from exc
        # Do not reveal that another tenant already owns this organization number.
        raise _not_found()

    brreg_data: dict[str, Any] | None = None
    if not manual_without_org:
        try:
            brreg_data = await brreg_service.lookup_org(org_number)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except Exception as exc:
            logger.error("BRREG lookup during farm creation failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Klarte ikke hente data fra Brønnøysund akkurat nå. Prøv igjen.",
            ) from exc
        if not brreg_data and not request.manual_entry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organisasjonsnummeret finnes ikke i Brønnøysundregisteret.",
            )

    farm = Farm(
        id=_deterministic_farm_id(org_number),
        name=request.name.strip() or (brreg_data or {}).get("name", ""),
        org_number=org_number,
        address=request.address or (brreg_data or {}).get("address", ""),
        postal_code=request.postal_code or (brreg_data or {}).get("postal_code", ""),
        city=request.city or (brreg_data or {}).get("city", ""),
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
        farm_status="provisioning",
        created_by_user_id=user_id,
    )
    document = farm.to_dict()
    try:
        service.farms.create_item(document)
    except exceptions.CosmosResourceExistsError:
        # A parallel retry created it; re-enter the idempotent existing-farm path.
        existing = service.get_farm_by_org_number(org_number)
        if existing is not None:
            return await create_farm(request, idempotency_key, current)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Gården kunne ikke opprettes trygt.")

    try:
        service.create_owner_membership(farm=document, user_id=user_id)
    except Exception as exc:
        # Keep the farm provisioning for an authorised retry; never grant access
        # by recreating the owner relationship from client-provided data.
        logger.error("Farm %s remains provisioning after membership failure: %s", farm.id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gårdsoppsettet er under behandling. Prøv igjen.",
        ) from exc

    document["farm_status"] = "active"
    document["updated_at"] = datetime.now(timezone.utc).isoformat()
    service.farms.upsert_item(document)
    _write_audit_event("FarmCreated", farm.id, user_id)
    _write_audit_event("FarmMembershipCreated", farm.id, user_id)
    return _farm_response(document)


@router.get("", response_model=list[FarmResponse])
def list_farms(current: CurrentIdentity = Depends(get_current_identity)) -> list[FarmResponse]:
    """Return only farms where the session user has an active FarmUser record."""
    service = MembershipService()
    farms: list[FarmResponse] = []
    for membership in service.list_active_memberships_for_user(current.user["user_id"]):
        farm = service.get_farm(membership["farm_id"])
        if farm is not None:
            farms.append(_farm_response(farm))
    return farms


@router.get("/{farm_id}/members", response_model=list[FarmMemberResponse])
def list_farm_members(
    farm_id: str,
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.MEMBER_LIST)),
) -> list[FarmMemberResponse]:
    service = MembershipService()
    return [
        FarmMemberResponse(
            user_id=str(member["user_id"]),
            farm_role=str(member.get("farm_role") or ""),
            membership_status=str(member.get("membership_status") or ""),
            created_at=member.get("created_at"),
        )
        for member in service.list_members_for_farm(farm_id)
    ]


@router.patch("/{farm_id}", response_model=FarmResponse)
def update_farm(
    farm_id: str,
    request: FarmUpdateRequest,
    access: AuthorizedFarm = Depends(
        require_farm_permission(
            Permission.FARM_UPDATE, require_csrf_protection=True, require_active_farm=True
        )
    ),
) -> FarmResponse:
    document = dict(access.farm)
    for field, value in request.model_dump(exclude_unset=True).items():
        document[field] = str(value) if field == "billing_email" and value is not None else value
    document["updated_at"] = datetime.now(timezone.utc).isoformat()
    document["version"] = int(document.get("version") or 1) + 1
    MembershipService().farms.upsert_item(document)
    _write_audit_event("FarmUpdated", farm_id, access.current.user["user_id"])
    return _farm_response(document)


@router.get("/{farm_id}", response_model=FarmResponse)
def get_farm(
    farm_id: str,
    access: AuthorizedFarm = Depends(require_farm_permission(Permission.FARM_READ)),
) -> FarmResponse:
    del farm_id
    return _farm_response(access.farm)
