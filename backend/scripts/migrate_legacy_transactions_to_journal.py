"""Controlled migration of legacy accounting_transaction documents to journal entries.

Dry-run by default. Apply requires explicit --apply. Never deletes legacy data
and never guesses ambiguous records: ambiguous rows are skipped and reported.

Usage:
    python -m scripts.migrate_legacy_transactions_to_journal --farm-id <farm_id> [--apply]
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal, ROUND_HALF_UP

from app.db.cosmos_client import get_transactions_container
from app.services import journal_service
from app.services.accounting_catalog import (
    account_exists,
    normalize_legacy_vat_code,
)
from app.services.journal_service import to_ore

INPUT_VAT_ACCOUNT = "2710"
DEFAULT_SUPPLIER_DEBT = "2400"


def _classify(tx: dict) -> tuple[str, str]:
    """Return (status, reason) for a legacy transaction."""
    if not account_exists(tx.get("account_code")):
        return "skipped", "unknown_account"
    vat_code = tx.get("mva_code")
    if vat_code:
        direction = "input" if tx.get("transaction_type") == "expense" else "output"
        if normalize_legacy_vat_code(str(vat_code), direction=direction) is None:
            return "skipped", "ambiguous_vat_code"
    if not tx.get("amount"):
        return "skipped", "missing_amount"
    return "migratable", ""


def migrate(farm_id: str, apply: bool) -> dict:
    container = get_transactions_container()
    items = list(
        container.query_items(
            query="SELECT * FROM c WHERE c.farm_id = @farm_id AND c.type = 'accounting_transaction'",
            parameters=[{"name": "@farm_id", "value": farm_id}],
            partition_key=farm_id,
        )
    )
    report = {"would_migrate": 0, "already_migrated": 0, "skipped": [], "errors": []}

    for tx in items:
        source_id = str(tx.get("source_id") or tx.get("id"))
        source_key = f"voucher:{source_id}:booking"
        try:
            existing = journal_service.entry_by_source_key(farm_id, source_key)
        except Exception:
            existing = None
        if existing:
            report["already_migrated"] += 1
            continue

        verdict, reason = _classify(tx)
        if verdict == "skipped":
            report["skipped"].append({"id": tx.get("id"), "reason": reason})
            continue

        # Conservative mapping: expense with no known counter account is only
        # migrated when document_type clearly implies one; otherwise skipped.
        document_type = str(tx.get("document_type") or "").lower()
        if document_type == "receipt":
            counter = "1920"
        elif document_type == "invoice":
            counter = DEFAULT_SUPPLIER_DEBT
        else:
            report["skipped"].append({"id": tx.get("id"), "reason": "ambiguous_counter_account"})
            continue

        total_ore = to_ore(tx.get("amount"))
        vat_code = tx.get("mva_code")
        direction = "input" if tx.get("transaction_type") == "expense" else "output"
        resolved = normalize_legacy_vat_code(str(vat_code), direction=direction) if vat_code else None

        net_ore = total_ore
        vat_ore = 0
        if resolved and resolved != "none":
            from app.services.accounting_catalog import get_vat_code

            rate = Decimal(get_vat_code(resolved)["rate"]) / Decimal(100)
            net_dec = (Decimal(total_ore) / (Decimal(1) + rate)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            net_ore = int(net_dec)
            vat_ore = total_ore - net_ore

        lines = []
        if tx.get("transaction_type") == "expense":
            lines.append({"account_code": tx["account_code"], "debit_ore": net_ore, "credit_ore": 0, "vat_code": "none"})
            if vat_ore > 0:
                lines.append({"account_code": INPUT_VAT_ACCOUNT, "debit_ore": vat_ore, "credit_ore": 0, "vat_code": resolved, "vat_amount_ore": vat_ore})
            lines.append({"account_code": counter, "debit_ore": 0, "credit_ore": total_ore, "vat_code": "none"})
        else:
            lines.append({"account_code": counter, "debit_ore": total_ore, "credit_ore": 0, "vat_code": "none"})
            lines.append({"account_code": tx["account_code"], "debit_ore": 0, "credit_ore": net_ore, "vat_code": "none"})
            if vat_ore > 0:
                lines.append({"account_code": "2700", "debit_ore": 0, "credit_ore": vat_ore, "vat_code": resolved, "vat_amount_ore": vat_ore})

        if apply:
            try:
                journal_service.post_entry(
                    farm_id=farm_id,
                    posting_date=str(tx.get("voucher_date") or "1970-01-01"),
                    document_date=tx.get("voucher_date"),
                    source_type="voucher",
                    source_id=source_id,
                    source_event="booking",
                    source_key=source_key,
                    description=str(tx.get("description") or "Legacy migrasjon"),
                    lines=lines,
                    user_id="migration-script",
                    source_revision=1,
                )
                report["would_migrate"] += 1
            except Exception as exc:
                report["errors"].append({"id": tx.get("id"), "error": str(exc)})
        else:
            report["would_migrate"] += 1

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--farm-id", required=True)
    parser.add_argument("--apply", action="store_true", help="Actually write journal entries (default: dry-run)")
    args = parser.parse_args()

    report = migrate(args.farm_id, apply=args.apply)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] would_migrate={report['would_migrate']} already_migrated={report['already_migrated']}")
    for item in report["skipped"]:
        print(f"  skipped: {item['id']} reason={item['reason']}")
    for item in report["errors"]:
        print(f"  error: {item['id']} {item['error']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())