"""Server-side Farm membership and permission dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status

from app.api.dependencies.identity import CurrentIdentity, get_current_identity, require_csrf
from app.core.permissions import Permission
from app.services.membership_service import (
    InactiveMembershipError,
    MembershipNotFoundError,
    MembershipService,
)


@dataclass(frozen=True)
class AuthorizedFarm:
    current: CurrentIdentity
    farm: dict
    membership: dict


def _not_found() -> HTTPException:
    # Deliberately indistinguishable: callers without access cannot discover a farm.
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gården ble ikke funnet.")


def get_active_farm_membership(
    farm_id: str, current: CurrentIdentity = Depends(get_current_identity)
) -> AuthorizedFarm:
    service = MembershipService()
    try:
        membership = service.get_active_membership(farm_id=farm_id, user_id=current.user["user_id"])
    except (MembershipNotFoundError, InactiveMembershipError) as exc:
        raise _not_found() from exc
    farm = service.get_farm(farm_id)
    if farm is None:
        raise _not_found()
    return AuthorizedFarm(current=current, farm=farm, membership=membership)


def get_authorized_farm(
    farm_id: str, current: CurrentIdentity = Depends(get_current_identity)
) -> AuthorizedFarm:
    return get_active_farm_membership(farm_id=farm_id, current=current)


def require_farm_permission(
    permission: Permission, *, require_csrf_protection: bool = False, require_active_farm: bool = False
):
    """Create a route dependency with a static, testable permission requirement."""

    principal_dependency = require_csrf if require_csrf_protection else get_current_identity

    def dependency(
        farm_id: str, current: CurrentIdentity = Depends(principal_dependency)
    ) -> AuthorizedFarm:
        service = MembershipService()
        try:
            membership = service.get_active_membership(farm_id=farm_id, user_id=current.user["user_id"])
        except (MembershipNotFoundError, InactiveMembershipError) as exc:
            raise _not_found() from exc

        farm = service.get_farm(farm_id)
        if farm is None:
            raise _not_found()
        if permission not in service.permissions_for_membership(membership):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Du har ikke tilgang til denne handlingen.",
            )
        if require_active_farm and str(farm.get("farm_status") or "active") != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Gården kan ikke endres i nåværende status.",
            )
        return AuthorizedFarm(current=current, farm=farm, membership=membership)

    return dependency
