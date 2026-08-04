"""Farm settings and owner-managed Norwegian bank accounts."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional

from azure.cosmos import exceptions
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator

from app.api.dependencies.farm_access import AuthorizedFarm, require_farm_permission
from app.core.permissions import Permission
from app.db.cosmos_client import get_bank_accounts_container, get_farm_settings_container

router = APIRouter()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_account_number(value: str) -> str:
    digits = re.sub(r"[ .]", "", value or "")
    if not digits.isdigit() or len(digits) != 11:
        raise ValueError("Kontonummer må bestå av nøyaktig 11 sifre.")
    weights = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    remainder = sum(int(digit) * weight for digit, weight in zip(digits[:10], weights)) % 11
    check = 11 - remainder
    check = 0 if check == 11 else check
    if check == 10 or int(digits[10]) != check:
        raise ValueError("Kontonummeret har ugyldig kontrollsiffer.")
    return digits


def mask_account_number(account_number: str) -> str:
    return f"**** **** {account_number[-3:]}"


class FarmSettingsPatch(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=120)
    legal_name: Optional[str] = Field(default=None, max_length=160)
    address_line_1: Optional[str] = Field(default=None, max_length=160)
    address_line_2: Optional[str] = Field(default=None, max_length=160)
    postal_code: Optional[str] = Field(default=None, max_length=10)
    city: Optional[str] = Field(default=None, max_length=100)
    contact_email: Optional[str] = Field(default=None, max_length=254)
    contact_phone: Optional[str] = Field(default=None, max_length=32)
    invoice_email: Optional[str] = Field(default=None, max_length=254)
    invoice_reference: Optional[str] = Field(default=None, max_length=80)
    payment_terms_days: Optional[int] = Field(default=None, ge=0, le=90)
    accounting_year_start: Optional[str] = Field(default=None, pattern=r"^\d{2}-\d{2}$")
    vat_registered: Optional[str] = Field(default=None, pattern=r"^(yes|no|unknown)$")
    vat_number: Optional[str] = Field(default=None, max_length=20)
    default_currency: Optional[str] = Field(default=None, pattern=r"^NOK$")
    default_language: Optional[str] = Field(default=None, pattern=r"^(nb|en)$")


class BankAccountCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    account_number: str
    is_default: bool = False

    @field_validator("account_number")
    @classmethod
    def validate_account(cls, value: str) -> str:
        return normalize_account_number(value)


class BankAccountPatch(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    is_default: Optional[bool] = None


def _settings(access: AuthorizedFarm) -> dict:
    container = get_farm_settings_container()
    identifier = f"farm-settings:{access.farm['id']}"
    try:
        return container.read_item(item=identifier, partition_key=access.farm["id"])
    except exceptions.CosmosResourceNotFoundError:
        document = {"id": identifier, "type": "farm_settings", "farm_id": access.farm["id"], "display_name": access.farm.get("name") or "", "legal_name": access.farm.get("name") or "", "address_line_1": access.farm.get("address") or "", "postal_code": access.farm.get("postal_code") or "", "city": access.farm.get("city") or "", "vat_registered": "unknown", "default_currency": "NOK", "default_language": "nb", "payment_terms_days": 14, "accounting_year_start": "01-01", "version": 1, "created_at": now(), "updated_at": now()}
        try:
            return container.create_item(document)
        except exceptions.CosmosResourceExistsError:
            return container.read_item(item=identifier, partition_key=access.farm["id"])


@router.get("/farms/{farm_id}/settings")
def get_farm_settings(access: AuthorizedFarm = Depends(require_farm_permission(Permission.FARM_SETTINGS_READ))) -> dict:
    return _settings(access)


@router.patch("/farms/{farm_id}/settings")
def patch_farm_settings(request: FarmSettingsPatch, access: AuthorizedFarm = Depends(require_farm_permission(Permission.FARM_SETTINGS_UPDATE, require_csrf_protection=True))) -> dict:
    document = dict(_settings(access))
    document.update(request.model_dump(exclude_unset=True))
    document["version"] = int(document.get("version") or 1) + 1
    document["updated_at"] = now()
    get_farm_settings_container().upsert_item(document)
    return document


def _account_response(item: dict, *, reveal: bool = False) -> dict:
    result = {"id": item["id"], "display_name": item["display_name"], "account_number_masked": mask_account_number(str(item["account_number"])), "is_default": bool(item.get("is_default")), "status": item.get("status", "active"), "version": item.get("version", 1)}
    if reveal:
        result["account_number"] = item["account_number"]
    return result


def _active_accounts(farm_id: str) -> list[dict]:
    return list(get_bank_accounts_container().query_items(query="SELECT * FROM c WHERE c.farm_id = @farm_id AND c.type = 'bank_account'", parameters=[{"name": "@farm_id", "value": farm_id}], partition_key=farm_id))


def _clear_default(farm_id: str, *, except_id: str) -> None:
    container = get_bank_accounts_container()
    for account in _active_accounts(farm_id):
        if account.get("id") != except_id and account.get("status") == "active" and account.get("is_default"):
            account["is_default"] = False
            account["updated_at"] = now()
            container.upsert_item(account)


@router.get("/farms/{farm_id}/bank-accounts")
def list_bank_accounts(access: AuthorizedFarm = Depends(require_farm_permission(Permission.BANK_ACCOUNT_READ))) -> list[dict]:
    return [_account_response(item) for item in _active_accounts(access.farm["id"])]


@router.post("/farms/{farm_id}/bank-accounts", status_code=status.HTTP_201_CREATED)
def create_bank_account(request: BankAccountCreate, access: AuthorizedFarm = Depends(require_farm_permission(Permission.BANK_ACCOUNT_CREATE, require_csrf_protection=True))) -> dict:
    farm_id = str(access.farm["id"])
    account_id = f"bank-account:{farm_id}:{uuid4()}"
    document = {"id": account_id, "type": "bank_account", "farm_id": farm_id, "display_name": request.display_name.strip(), "account_number": request.account_number, "is_default": request.is_default or not any(item.get("is_default") and item.get("status") == "active" for item in _active_accounts(farm_id)), "status": "active", "created_by_user_id": access.current.user["user_id"], "version": 1, "created_at": now(), "updated_at": now()}
    if document["is_default"]:
        _clear_default(farm_id, except_id=account_id)
    get_bank_accounts_container().create_item(document)
    return _account_response(document, reveal=True)


@router.patch("/farms/{farm_id}/bank-accounts/{account_id}")
def patch_bank_account(account_id: str, request: BankAccountPatch, access: AuthorizedFarm = Depends(require_farm_permission(Permission.BANK_ACCOUNT_UPDATE, require_csrf_protection=True))) -> dict:
    container = get_bank_accounts_container()
    try:
        document = container.read_item(item=account_id, partition_key=access.farm["id"])
    except exceptions.CosmosResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bankkontoen ble ikke funnet.") from exc
    if document.get("status") != "active" and request.is_default:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="En inaktiv konto kan ikke være standardkonto.")
    document.update(request.model_dump(exclude_unset=True))
    if document.get("is_default"):
        _clear_default(str(access.farm["id"]), except_id=account_id)
    document["version"] = int(document.get("version") or 1) + 1
    document["updated_at"] = now()
    container.upsert_item(document)
    return _account_response(document, reveal=True)


@router.delete("/farms/{farm_id}/bank-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_bank_account(account_id: str, access: AuthorizedFarm = Depends(require_farm_permission(Permission.BANK_ACCOUNT_DELETE, require_csrf_protection=True))) -> Response:
    container = get_bank_accounts_container()
    try:
        document = container.read_item(item=account_id, partition_key=access.farm["id"])
    except exceptions.CosmosResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bankkontoen ble ikke funnet.") from exc
    document.update({"status": "inactive", "is_default": False, "updated_at": now(), "version": int(document.get("version") or 1) + 1})
    container.upsert_item(document)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
