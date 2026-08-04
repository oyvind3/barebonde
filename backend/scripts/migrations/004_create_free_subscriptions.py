"""Assign missing free subscriptions to existing Farms in controlled batches.

Run manually from the repository root only after reviewing the target Cosmos
configuration.  It never creates containers and is not imported by Functions
startup or deployment.

    python backend/scripts/migrations/004_create_free_subscriptions.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.cosmos_client import get_farms_container, get_subscriptions_container
from app.services.subscription_service import SubscriptionService, SubscriptionUnavailableError


def _batches(items: Iterable[dict[str, Any]], batch_size: int) -> Iterable[list[dict[str, Any]]]:
    batch: list[dict[str, Any]] = []
    for item in items:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def migrate_free_subscriptions(
    *,
    farms_container: Any,
    subscription_service: SubscriptionService,
    dry_run: bool,
    batch_size: int,
    write=print,
) -> dict[str, int]:
    """Create only missing subscriptions and return non-sensitive counters."""
    farms = farms_container.query_items(
        query="SELECT c.id FROM c WHERE c.type = 'farm'",
        enable_cross_partition_query=True,
        max_item_count=batch_size,
    )
    counters = {"farms_scanned": 0, "would_create": 0, "created": 0, "existing": 0, "failed": 0}

    for batch in _batches(farms, batch_size):
        for farm in batch:
            farm_id = str(farm.get("id") or "")
            if not farm_id:
                counters["failed"] += 1
                continue
            counters["farms_scanned"] += 1
            try:
                existing = subscription_service.get_subscription(farm_id)
                if existing is not None:
                    counters["existing"] += 1
                    continue
                if dry_run:
                    counters["would_create"] += 1
                    continue
                result = subscription_service.ensure_free_subscription(farm_id=farm_id)
                counters["created" if result.created else "existing"] += 1
            except SubscriptionUnavailableError:
                counters["failed"] += 1

    mode = "Dry-run" if dry_run else "Apply"
    write(
        f"{mode} complete: farms_scanned={counters['farms_scanned']} "
        f"would_create={counters['would_create']} created={counters['created']} "
        f"existing={counters['existing']} failed={counters['failed']}"
    )
    return counters


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create missing free Farm subscriptions safely.")
    parser.add_argument("--dry-run", action="store_true", help="Report missing subscriptions without writing.")
    parser.add_argument("--batch-size", type=int, default=50, help="Farms to process before yielding work.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.batch_size < 1 or args.batch_size > 500:
        print("ERROR: --batch-size must be between 1 and 500.")
        return 2
    try:
        service = SubscriptionService(subscriptions_container=get_subscriptions_container())
        counters = migrate_free_subscriptions(
            farms_container=get_farms_container(),
            subscription_service=service,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
        )
    except Exception:
        print("ERROR: Subscription migration could not inspect Cosmos. Check configuration and connectivity.")
        return 1
    return 1 if counters["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
