"""Immutable, versioned product-plan catalogue.

Plan definitions are deliberately code-owned in this MVP.  Cosmos subscription
documents only reference a plan code and version; they never copy entitlement
flags that could silently drift from the catalogue.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


ACTIVE_PLAN_VERSION = "2026-08"


@dataclass(frozen=True)
class PlanDefinition:
    code: str
    display_name: str
    feature_summary: tuple[str, ...]
    entitlements: Mapping[str, bool]


def _entitlements(**values: bool) -> Mapping[str, bool]:
    return MappingProxyType(values)


_FREE = PlanDefinition(
    code="free",
    display_name="Gratis",
    feature_summary=("Gårdsoversikt", "Bilag og dokumenter", "Grunnrapporter"),
    entitlements=_entitlements(
        **{
            "farm.overview.enabled": True,
            "vouchers.enabled": True,
            "documents.enabled": True,
            "accounting.enabled": True,
            "reports.basic.enabled": True,
            "reports.advanced.enabled": False,
            "member_management.enabled": False,
            "ehf.enabled": False,
            "api_access.enabled": False,
            "integrations.enabled": False,
        }
    ),
)

_STANDARD = PlanDefinition(
    code="standard",
    display_name="Standard",
    feature_summary=("Alt i Gratis", "Avanserte rapporter", "Medlemsadministrasjon"),
    entitlements=_entitlements(
        **{
            "farm.overview.enabled": True,
            "vouchers.enabled": True,
            "documents.enabled": True,
            "accounting.enabled": True,
            "reports.basic.enabled": True,
            "reports.advanced.enabled": True,
            "member_management.enabled": True,
            "ehf.enabled": False,
            "api_access.enabled": False,
            "integrations.enabled": False,
        }
    ),
)

_PREMIUM = PlanDefinition(
    code="premium",
    display_name="Premium",
    feature_summary=("Alt i Standard", "Integrasjoner", "API-tilgang"),
    entitlements=_entitlements(
        **{
            "farm.overview.enabled": True,
            "vouchers.enabled": True,
            "documents.enabled": True,
            "accounting.enabled": True,
            "reports.basic.enabled": True,
            "reports.advanced.enabled": True,
            "member_management.enabled": True,
            "ehf.enabled": True,
            "api_access.enabled": True,
            "integrations.enabled": True,
        }
    ),
)

# Mapping proxies make accidental mutation fail immediately in runtime and tests.
PLAN_CATALOG: Mapping[str, Mapping[str, PlanDefinition]] = MappingProxyType(
    {
        ACTIVE_PLAN_VERSION: MappingProxyType(
            {"free": _FREE, "standard": _STANDARD, "premium": _PREMIUM}
        )
    }
)


def get_plan(plan_version: object, plan_code: object) -> PlanDefinition | None:
    """Return a configured plan, or ``None`` so callers fail closed."""
    version = str(plan_version or "")
    code = str(plan_code or "").strip().casefold()
    return PLAN_CATALOG.get(version, {}).get(code)


def public_plans() -> list[dict[str, object]]:
    """Return safe product metadata without provider or billing details."""
    plans = PLAN_CATALOG[ACTIVE_PLAN_VERSION]
    return [
        {
            "plan_code": plan.code,
            "display_name": plan.display_name,
            "feature_summary": list(plan.feature_summary),
        }
        for plan in plans.values()
    ]
