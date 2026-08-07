"""Farm-scoped customer register (MVP) with BRREG prefill support."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from azure.cosmos import exceptions
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.dependencies.farm_access import AuthorizedFarm, require_farm_permission
from app.core.permissions import Permission
from app.db.cosmos_client import get_customers_container
from app.services.brreg_service import brreg_service

router = APIRouter()

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ORG_NUMBER_PATTERN = re.compile(r"^\d{9}$")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_org_number(value: Optional[str]) -> str:
    """Normalize a Norwegian org number to 9 digits, or empty string.
    
    Note: This function is kept for backwards compatibility but is no longer used
    in create_customer/patch_customer endpoints since Pydantic now validates the pattern.
    """
    cleaned = re.sub(r"[\s.]", "", value or "")
    if not cleaned:
        return ""
    if not ORG_NUMBER_PATTERN.match(cleaned):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organisasjonsnummer må bestå av 9 sifre.",
        )
    return cleaned


def validate_email(value: Optional[str]) -> str:
    email = (value or "").strip()
    if email and not EMAIL_PATTERN.match(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-postadressen er ugyldig.",
        )
    return email


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    org_number: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None, max_length=254)
    address: Optional[str] = Field(default=None, max_length=160)
    postal_code: Optional[str] = Field(default=None, max_length=10)
    city: Optional[str] = Field(default=None, max_length=100)
    country_code: Optional[str] = Field(default="NO", max_length=2)
    brreg_verified: bool = False


class CustomerPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    org_number: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None, max_length=254)
    address: Optional[str] = Field(default=None, max_length=160)
    postal_code: Optional[str] = Field(default=None, max_length=10)
    city: Optional[str] = Field(default=None, max_length=100)
    country_code: Optional[str] = Field(default=None, max_length=2)


def _customer_response(item: dict) -> dict:
    return {
        "id": item["id"],
        "name": item.get("name") or "",
        "org_number": item.get("org_number") or "",
        "email": item.get("email") or "",
        "address": item.get("address") or "",
        "postal_code": item.get("postal_code") or "",
        "city": item.get("city") or "",
        "country_code": item.get("country_code") or "NO",
        "brreg_verified": bool(item.get("brreg_verified")),
        "status": item.get("status") or "active",
        "version": item.get("version") or 1,
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
    }


def _find_by_org_number(farm_id: str, org_number: str) -> Optional[dict]:
    if not org_number:
        return None
    results = list(
        get_customers_container().query_items(
            query="SELECT * FROM c WHERE c.farm_id = @farm_id AND c.type = 'customer' AND c.org_number = @org_number",
            parameters=[
                {"name": "@farm_id", "value": farm_id},
                {"name": "@org_number", "value": org_number},
            ],
            partition_key=farm_id,
        )
    )
    return results[0] if results else None


def _read_customer(farm_id: str, customer_id: str) -> dict:
    try:
        document = get_customers_container().read_item(item=customer_id, partition_key=farm_id)
    except exceptions.CosmosResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kunden ble ikke funnet.") from exc
    if document.get("type") != "customer":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kunden ble ikke funnet.")
    return document


@router.get("/farms/{farm_id}/customers")
def list_customers(
    access: AuthorizedFarm = Depends(require_farm_permission(Permission.CUSTOMER_READ)),
) -> dict:
    farm_id = str(access.farm["id"])
    items = list(
        get_customers_container().query_items(
            query="SELECT * FROM c WHERE c.farm_id = @farm_id AND c.type = 'customer'",
            parameters=[{"name": "@farm_id", "value": farm_id}],
            partition_key=farm_id,
        )
    )
    items.sort(key=lambda item: (item.get("name") or "").lower())
    return {"customers": [_customer_response(item) for item in items]}


@router.get("/farms/{farm_id}/customers/brreg-search")
async def brreg_search(
    query: str = Query(min_length=2, max_length=100),
    access: AuthorizedFarm = Depends(require_farm_permission(Permission.CUSTOMER_READ)),
) -> dict:
    try:
        results = await brreg_service.search_orgs(query, size=10)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Kunne ikke søke i Enhetsregisteret. Prøv igjen senere.",
        )
    return {"results": results}


@router.post("/farms/{farm_id}/customers", status_code=status.HTTP_201_CREATED)
def create_customer(
    request: CustomerCreate,
    access: AuthorizedFarm = Depends(require_farm_permission(Permission.CUSTOMER_CREATE, require_csrf_protection=True)),
) -> dict:
    farm_id = str(access.farm["id"])
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kunden må ha et navn.")

    # Normalize and validate org_number (treat empty/whitespace as None)
    org_number_raw = (request.org_number or "").strip()
    if org_number_raw and not ORG_NUMBER_PATTERN.match(org_number_raw):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organisasjonsnummer må bestå av nøyaktig 9 sifre.",
        )
    org_number = org_number_raw or ""
    email = validate_email(request.email)

    if org_number:
        existing = _find_by_org_number(farm_id, org_number)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="En kunde med dette organisasjonsnummeret finnes allerede.",
            )

    customer_id = f"customer:{farm_id}:{uuid4()}"
    document = {
        "id": customer_id,
        "type": "customer",
        "farm_id": farm_id,
        "name": name,
        "org_number": org_number,
        "email": email,
        "address": (request.address or "").strip(),
        "postal_code": (request.postal_code or "").strip(),
        "city": (request.city or "").strip(),
        "country_code": (request.country_code or "NO").strip().upper() or "NO",
        "brreg_verified": bool(request.brreg_verified),
        "status": "active",
        "created_by_user_id": access.current.user["user_id"],
        "version": 1,
        "created_at": now(),
        "updated_at": now(),
    }
    try:
        get_customers_container().create_item(document)
    except exceptions.CosmosHttpResponseError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="customers_unavailable",
        ) from exc
    return _customer_response(document)


@router.get("/farms/{farm_id}/customers/{customer_id}")
def get_customer(
    customer_id: str,
    access: AuthorizedFarm = Depends(require_farm_permission(Permission.CUSTOMER_READ)),
) -> dict:
    document = _read_customer(str(access.farm["id"]), customer_id)
    return _customer_response(document)


@router.patch("/farms/{farm_id}/customers/{customer_id}")
def patch_customer(
    customer_id: str,
    request: CustomerPatch,
    access: AuthorizedFarm = Depends(require_farm_permission(Permission.CUSTOMER_UPDATE, require_csrf_protection=True)),
) -> dict:
    farm_id = str(access.farm["id"])
    container = get_customers_container()
    document = _read_customer(farm_id, customer_id)

    updates = request.model_dump(exclude_unset=True)

    if "org_number" in updates:
        # Normalize and validate org_number (treat empty/whitespace as None)
        new_org_raw = (updates["org_number"] or "").strip()
        if new_org_raw and not ORG_NUMBER_PATTERN.match(new_org_raw):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organisasjonsnummer må bestå av nøyaktig 9 sifre.",
            )
        new_org = new_org_raw or ""
        if new_org and new_org != (document.get("org_number") or ""):
            existing = _find_by_org_number(farm_id, new_org)
            if existing and existing.get("id") != customer_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="En kunde med dette organisasjonsnummeret finnes allerede.",
                )
        document["org_number"] = new_org
        updates.pop("org_number")

    if "email" in updates:
        document["email"] = validate_email(updates.pop("email"))

    if "name" in updates:
        name = (updates.pop("name") or "").strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kunden må ha et navn.")
        document["name"] = name

    for key in ("address", "postal_code", "city"):
        if key in updates:
            document[key] = (updates.pop(key) or "").strip()

    if "country_code" in updates:
        document["country_code"] = (updates.pop("country_code") or "NO").strip().upper() or "NO"

    document["version"] = int(document.get("version") or 1) + 1
    document["updated_at"] = now()
    container.upsert_item(document)
    return _customer_response(document)