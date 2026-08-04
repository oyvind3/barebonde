"""Compute subscription entitlements from the static plan catalogue."""

from __future__ import annotations

import logging
from typing import Any

from app.subscriptions.plans import get_plan

logger = logging.getLogger(__name__)

ACCESS_MODES_BY_STATUS: dict[str, frozenset[str]] = {
    "trialing": frozenset({"read", "export", "mutate"}),
    "active": frozenset({"read", "export", "mutate"}),
    "past_due": frozenset({"read", "export", "mutate"}),
    "grace_period": frozenset({"read", "export"}),
    "canceled": frozenset({"read", "export"}),
    "expired": frozenset({"read", "export"}),
    "suspended": frozenset(),
}


def get_effective_entitlements(subscription: dict[str, Any]) -> dict[str, bool]:
    """Return a new safe mapping; unknown plan versions and codes get no access."""
    plan = get_plan(subscription.get("plan_version"), subscription.get("plan_code"))
    if plan is None:
        logger.error(
            "Subscription has unknown plan configuration (version=%r, code=%r).",
            subscription.get("plan_version"),
            subscription.get("plan_code"),
        )
        return {}
    return dict(plan.entitlements)


def has_entitlement(subscription: dict[str, Any], entitlement: str) -> bool:
    return get_effective_entitlements(subscription).get(entitlement, False)


def get_subscription_access(subscription: dict[str, Any]) -> frozenset[str]:
    """Central conservative status policy for all current and future gates."""
    status = str(subscription.get("subscription_status") or "").casefold()
    return ACCESS_MODES_BY_STATUS.get(status, frozenset())


def subscription_allows(subscription: dict[str, Any], access_mode: str) -> bool:
    return access_mode in get_subscription_access(subscription)
