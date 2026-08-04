"""Farm-owned subscription persistence with idempotent free-plan assignment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any
from uuid import uuid4

from azure.cosmos import exceptions

from app.db.cosmos_client import get_audit_logs_container, get_subscriptions_container
from app.db.cosmos_models import Subscription
from app.services.entitlement_service import get_subscription_access
from app.subscriptions.plans import ACTIVE_PLAN_VERSION

logger = logging.getLogger(__name__)


class SubscriptionError(Exception):
    """Expected subscription storage or configuration failure."""


class SubscriptionUnavailableError(SubscriptionError):
    """Subscription storage could not safely serve a request."""


@dataclass(frozen=True)
class EnsuredSubscription:
    subscription: dict[str, Any]
    created: bool


class SubscriptionService:
    def __init__(self, *, subscriptions_container: Any | None = None, audit_logs_container: Any | None = None):
        self.subscriptions = subscriptions_container or get_subscriptions_container()
        self.audit_logs = audit_logs_container or get_audit_logs_container()

    @staticmethod
    def subscription_id(farm_id: str) -> str:
        return Subscription.subscription_id(farm_id)

    def get_subscription(self, farm_id: str) -> dict[str, Any] | None:
        try:
            document = self.subscriptions.read_item(
                item=self.subscription_id(farm_id), partition_key=farm_id
            )
        except exceptions.CosmosResourceNotFoundError:
            return None
        except Exception as exc:
            logger.exception("Could not read subscription for Farm %s.", farm_id)
            raise SubscriptionUnavailableError("Subscription storage is unavailable.") from exc
        if not isinstance(document, dict) or document.get("farm_id") != farm_id:
            logger.error("Invalid subscription document encountered for Farm %s.", farm_id)
            raise SubscriptionUnavailableError("Subscription data is invalid.")
        return dict(document)

    def ensure_free_subscription(self, farm_id: str, actor_user_id: str | None = None) -> EnsuredSubscription:
        """Create a free subscription once, without touching any existing plan."""
        existing = self.get_subscription(farm_id)
        if existing is not None:
            return EnsuredSubscription(subscription=existing, created=False)

        document = Subscription(
            farm_id=farm_id,
            plan_code="free",
            plan_version=ACTIVE_PLAN_VERSION,
            subscription_status="active",
        ).to_dict()
        try:
            created = self.subscriptions.create_item(document)
        except exceptions.CosmosResourceExistsError:
            existing = self.get_subscription(farm_id)
            if existing is not None:
                return EnsuredSubscription(subscription=existing, created=False)
            logger.error("Subscription create conflicted but no document could be read for Farm %s.", farm_id)
            raise SubscriptionUnavailableError("Subscription could not be confirmed.")
        except Exception as exc:
            logger.exception("Could not create free subscription for Farm %s.", farm_id)
            raise SubscriptionUnavailableError("Subscription storage is unavailable.") from exc

        persisted = dict(created) if isinstance(created, dict) else document
        self._write_free_plan_audit(farm_id=farm_id, actor_user_id=actor_user_id)
        return EnsuredSubscription(subscription=persisted, created=True)

    def get_or_create_free_subscription(self, farm_id: str, actor_user_id: str | None = None) -> EnsuredSubscription:
        return self.ensure_free_subscription(farm_id=farm_id, actor_user_id=actor_user_id)

    @staticmethod
    def get_subscription_access(subscription: dict[str, Any]) -> frozenset[str]:
        return get_subscription_access(subscription)

    def _write_free_plan_audit(self, *, farm_id: str, actor_user_id: str | None) -> None:
        try:
            self.audit_logs.create_item(
                {
                    "id": str(uuid4()),
                    "type": "audit_log",
                    "event_type": "FreePlanAssigned",
                    "farm_id": farm_id,
                    "actor_user_id": actor_user_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception as exc:
            # An audit failure must not cause an already persisted subscription
            # to be reported as failed and then retried unnecessarily.
            logger.warning("Could not persist FreePlanAssigned audit event for Farm %s: %s", farm_id, exc)
