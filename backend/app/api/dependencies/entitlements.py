"""Subscription entitlement dependencies layered on authoritative Farm access."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status

from app.api.dependencies.farm_access import AuthorizedFarm, require_farm_permission
from app.core.permissions import Permission
from app.services.entitlement_service import get_effective_entitlements, subscription_allows
from app.services.subscription_service import SubscriptionService, SubscriptionUnavailableError


@dataclass(frozen=True)
class AuthorizedEntitlement:
    farm_access: AuthorizedFarm
    subscription: dict
    entitlements: dict[str, bool]


def require_entitlement(
    entitlement: str,
    *,
    permission: Permission,
    access_mode: str = "read",
    require_csrf_protection: bool = False,
):
    """Require a Farm permission before consulting its subscription entitlement."""
    if access_mode not in {"read", "export", "mutate"}:
        raise ValueError("Unsupported subscription access mode.")

    permission_dependency = require_farm_permission(
        permission,
        require_csrf_protection=require_csrf_protection,
    )

    def dependency(
        access: AuthorizedFarm = Depends(permission_dependency),
    ) -> AuthorizedEntitlement:
        # The nested permission dependency executes before any subscription
        # read/write, so unauthorized Farm IDs never create subscription data.
        try:
            ensured = SubscriptionService().ensure_free_subscription(
                farm_id=str(access.farm["id"]),
                actor_user_id=str(access.current.user["user_id"]),
            )
        except SubscriptionUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Abonnementstjenesten er midlertidig utilgjengelig. Prøv igjen.",
            ) from exc

        subscription = ensured.subscription
        if not subscription_allows(subscription, access_mode):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Abonnementet gir ikke tilgang til denne handlingen.",
            )

        entitlements = get_effective_entitlements(subscription)
        if not entitlements.get(entitlement, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Denne funksjonen er ikke inkludert i abonnementet.",
            )
        return AuthorizedEntitlement(
            farm_access=access,
            subscription=subscription,
            entitlements=entitlements,
        )

    return dependency
