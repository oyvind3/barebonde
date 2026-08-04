"""Safe read-only subscription and entitlement API endpoints."""

from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies.farm_access import AuthorizedFarm, get_authorized_farm, require_farm_permission
from app.api.identity_models import SubscriptionResponse, subscription_response
from app.core.permissions import Permission
from app.services.entitlement_service import get_effective_entitlements
from app.services.subscription_service import SubscriptionService, SubscriptionUnavailableError
from app.subscriptions.plans import ACTIVE_PLAN_VERSION, public_plans

router = APIRouter()


class PlanResponse(BaseModel):
    plan_code: str
    display_name: str
    feature_summary: List[str]


class PlansResponse(BaseModel):
    plan_version: str
    plans: List[PlanResponse]


class EntitlementsResponse(BaseModel):
    entitlements: Dict[str, bool] = Field(default_factory=dict)


def _ensure_subscription(access: AuthorizedFarm) -> dict:
    try:
        return SubscriptionService().ensure_free_subscription(
            farm_id=str(access.farm["id"]),
            actor_user_id=str(access.current.user["user_id"]),
        ).subscription
    except SubscriptionUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Abonnementstjenesten er midlertidig utilgjengelig. Prøv igjen.",
        ) from exc


@router.get("/plans", response_model=PlansResponse)
def list_plans() -> PlansResponse:
    return PlansResponse(plan_version=ACTIVE_PLAN_VERSION, plans=public_plans())


@router.get("/farms/{farm_id}/subscription", response_model=SubscriptionResponse)
def get_subscription(
    access: AuthorizedFarm = Depends(require_farm_permission(Permission.SUBSCRIPTION_READ)),
) -> SubscriptionResponse:
    return subscription_response(_ensure_subscription(access))


@router.get("/farms/{farm_id}/entitlements", response_model=EntitlementsResponse)
def get_entitlements(
    access: AuthorizedFarm = Depends(get_authorized_farm),
) -> EntitlementsResponse:
    return EntitlementsResponse(entitlements=get_effective_entitlements(_ensure_subscription(access)))
