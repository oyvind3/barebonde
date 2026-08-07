"""Double-entry journal engine for Barebonde.

JournalEntry documents live in the ``journal_entries`` container, partitioned
by ``farm_id``. Lines are embedded in the entry document so that one entry is
one atomic unit. Posted entries are immutable; corrections are new entries.

Money is stored as integer ore (1/100 NOK). Floats are never used as the
authoritative representation.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError

from app.db.cosmos_client import get_journal_entries_container, get_accounting_periods_container
from app.services.accounting_catalog import account_exists, get_vat_code

logger = logging.getLogger(__name__)

JOURNAL_SCHEMA_VERSION = 1
STATUS_POSTED = "posted"

SOURCE_TYPE_VOUCHER = "voucher"
SOURCE_TYPE_SALES_INVOICE = "sales_invoice"


class JournalValidationError(ValueError):
    """Raised when a journal entry violates an accounting invariant."""


class PeriodLockedError(JournalValidationError):
    """Raised when posting is attempted into a locked accounting period."""


class DuplicateSourceError(JournalValidationError):
    """Raised when the same source key is posted twice (idempotency guard)."""


# ---------------------------------------------------------------------------
# Money helpers
# ---------------------------------------------------------------------------

def to_ore(value: Any) -> int:
    """Convert a kroner value (float/str/Decimal/int) to integer ore, ROUND_HALF_UP."""
    if value is None:
        return 0
    if isinstance(value, int):
        return value * 100
    dec = Decimal(str(value))
    return int((dec * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def ore_to_kroner(ore: int) -> float:
    return ore / 100.0


def validate_date(value: Optional[str], field: str = "posting_date") -> str:
    if not value:
        raise JournalValidationError(f"{field} er påkrevd")
    try:
        date.fromisoformat(str(value)[:10])
    except ValueError as exc:
        raise JournalValidationError(f"{field} er ikke en gyldig dato: {value}") from exc
    return str(value)[:10]


def period_of(posting_date: str) -> str:
    return posting_date[:7]


# ---------------------------------------------------------------------------
# Line validation
# ---------------------------------------------------------------------------

def validate_lines(lines: list[dict[str, Any]]) -> tuple[int, int]:
    """Validate journal lines and return (total_debit_ore, total_credit_ore).

    Raises JournalValidationError on any invariant violation.
    """
    if not lines or len(lines) < 2:
        raise JournalValidationError("En journalpost må ha minst to linjer")

    total_debit = 0
    total_credit = 0
    for index, line in enumerate(lines):
        account_code = str(line.get("account_code") or "").strip()
        if not account_exists(account_code):
            raise JournalValidationError(f"Linje {index + 1}: ukjent konto '{account_code}'")

        debit = int(line.get("debit_ore") or 0)
        credit = int(line.get("credit_ore") or 0)
        if debit < 0 or credit < 0:
            raise JournalValidationError(f"Linje {index + 1}: negative beløp er ikke tillatt")
        if debit > 0 and credit > 0:
            raise JournalValidationError(f"Linje {index + 1}: kan ikke ha både debet og kredit")
        if debit == 0 and credit == 0:
            raise JournalValidationError(f"Linje {index + 1}: null-linje er ikke tillatt")

        vat_code = line.get("vat_code")
        if vat_code and vat_code != "none" and get_vat_code(vat_code) is None:
            raise JournalValidationError(f"Linje {index + 1}: ukjent MVA-kode '{vat_code}'")

        total_debit += debit
        total_credit += credit

    if total_debit != total_credit:
        raise JournalValidationError(
            f"Journalposten er ikke balansert: debet {total_debit} != kredit {total_credit}"
        )
    if total_debit <= 0:
        raise JournalValidationError("Journalposten må ha et positivt totalbeløp")

    return total_debit, total_credit


# ---------------------------------------------------------------------------
# Period status
# ---------------------------------------------------------------------------

def period_is_open(farm_id: str, posting_date: str) -> bool:
    period = period_of(posting_date)
    container = get_accounting_periods_container()
    try:
        doc = container.read_item(
            item=f"accounting-period:{farm_id}:{period}",
            partition_key=farm_id,
        )
        return doc.get("status") != "locked"
    except CosmosResourceNotFoundError:
        return True


def require_open_period(farm_id: str, posting_date: str) -> None:
    if not period_is_open(farm_id, posting_date):
        raise PeriodLockedError(
            f"Regnskapsperioden {period_of(posting_date)} er låst. "
            "Bokfør i en åpen periode."
        )


# ---------------------------------------------------------------------------
# Journal number sequence (ETag optimistic concurrency)
# ---------------------------------------------------------------------------

def allocate_journal_number(farm_id: str, year: int) -> str:
    """Allocate the next sequential journal number for a farm/year.

    Uses an ETag-guarded sequence document so concurrent postings never reuse
    a number. Retries on conflict.
    """
    container = get_journal_entries_container()
    sequence_id = f"journal-sequence:{farm_id}:{year}"

    for _attempt in range(10):
        try:
            doc = container.read_item(item=sequence_id, partition_key=farm_id)
            etag = doc.get("_etag")
            next_number = int(doc.get("last_number") or 0) + 1
            doc["last_number"] = next_number
            doc["updated_at"] = datetime.now(timezone.utc).isoformat()
            container.replace_item(
                item=sequence_id,
                body=doc,
                match_condition="IfMatch",
                etag=etag,
            )
            return f"{year}-{next_number:06d}"
        except CosmosResourceNotFoundError:
            try:
                container.create_item(
                    body={
                        "id": sequence_id,
                        "type": "journal_sequence",
                        "farm_id": farm_id,
                        "year": year,
                        "last_number": 1,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                return f"{year}-000001"
            except Exception:
                # Another writer created it first; retry read path.
                continue
        except CosmosAccessConditionFailedError:
            continue

    raise JournalValidationError("Kunne ikke allokere journalnummer (for mange samtidige forsøk)")


# ---------------------------------------------------------------------------
# Posting
# ---------------------------------------------------------------------------

def post_entry(
    *,
    farm_id: str,
    posting_date: str,
    document_date: Optional[str],
    source_type: str,
    source_id: str,
    source_event: str,
    source_key: str,
    description: str,
    lines: list[dict[str, Any]],
    user_id: str,
    correction_of: Optional[str] = None,
    correction_reason: Optional[str] = None,
    source_revision: int = 1,
    source_snapshot: Optional[dict[str, Any]] = None,
    currency: str = "NOK",
) -> dict[str, Any]:
    """Validate and post a balanced journal entry. Idempotent per source_key."""
    posting_date = validate_date(posting_date, "posting_date")
    document_date = validate_date(document_date, "document_date") if document_date else posting_date
    require_open_period(farm_id, posting_date)

    total_debit, total_credit = validate_lines(lines)

    entry_id = f"journal-entry:{source_key}"
    container = get_journal_entries_container()

    # Idempotency: return existing entry for the same source key.
    existing = read_entry(farm_id, entry_id)
    if existing:
        return existing

    year = int(posting_date[:4])
    journal_number = allocate_journal_number(farm_id, year)
    now = datetime.now(timezone.utc).isoformat()

    normalized_lines = []
    for index, line in enumerate(lines):
        vat_code = line.get("vat_code") or "none"
        vat_meta = get_vat_code(vat_code) if vat_code != "none" else None
        normalized_lines.append(
            {
                "line_no": index + 1,
                "account_code": str(line["account_code"]).strip(),
                "debit_ore": int(line.get("debit_ore") or 0),
                "credit_ore": int(line.get("credit_ore") or 0),
                "description": line.get("description") or description,
                "vat_code": vat_code,
                "vat_rate": vat_meta.get("rate") if vat_meta else None,
                "vat_amount_ore": int(line.get("vat_amount_ore") or 0),
                "source_line_id": line.get("source_line_id"),
            }
        )

    entry = {
        "id": entry_id,
        "type": "journal_entry",
        "farm_id": farm_id,
        "journal_number": journal_number,
        "journal_year": year,
        "status": STATUS_POSTED,
        "posting_date": posting_date,
        "document_date": document_date,
        "source_type": source_type,
        "source_id": source_id,
        "source_event": source_event,
        "source_key": source_key,
        "description": description,
        "currency": currency,
        "lines": normalized_lines,
        "total_debit_ore": total_debit,
        "total_credit_ore": total_credit,
        "correction_of": correction_of,
        "correction_reason": correction_reason,
        "source_revision": source_revision,
        "source_snapshot": source_snapshot or {},
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "created_by_user_id": user_id,
        "posted_by_user_id": user_id,
        "created_at": now,
        "posted_at": now,
    }

    try:
        container.create_item(body=entry)
    except Exception:
        # Concurrent writer may have created it between our read and create.
        existing = read_entry(farm_id, entry_id)
        if existing:
            return existing
        raise

    logger.info("Journal entry %s posted for farm %s (%s)", journal_number, farm_id, source_key)
    return entry


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

def read_entry(farm_id: str, entry_id: str) -> Optional[dict[str, Any]]:
    container = get_journal_entries_container()
    try:
        return container.read_item(item=entry_id, partition_key=farm_id)
    except CosmosResourceNotFoundError:
        return None


def entry_by_source_key(farm_id: str, source_key: str) -> Optional[dict[str, Any]]:
    return read_entry(farm_id, f"journal-entry:{source_key}")


def list_entries(
    farm_id: str,
    *,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    account_code: Optional[str] = None,
    source_type: Optional[str] = None,
    source_id: Optional[str] = None,
    journal_number: Optional[str] = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """List journal entries for a farm with simple in-memory filtering."""
    container = get_journal_entries_container()
    query = (
        "SELECT * FROM c WHERE c.type = 'journal_entry' "
        "AND c.farm_id = @farm_id ORDER BY c.posted_at DESC OFFSET 0 LIMIT 5000"
    )
    items = list(
        container.query_items(
            query=query,
            parameters=[{"name": "@farm_id", "value": farm_id}],
            partition_key=farm_id,
            enable_cross_partition_query=False,
        )
    )

    results = []
    for item in items:
        if date_from and item.get("posting_date", "") < date_from:
            continue
        if date_to and item.get("posting_date", "") > date_to:
            continue
        if source_type and item.get("source_type") != source_type:
            continue
        if source_id and item.get("source_id") != source_id:
            continue
        if journal_number and item.get("journal_number") != journal_number:
            continue
        if account_code:
            if not any(line.get("account_code") == account_code for line in item.get("lines", [])):
                continue
        results.append(item)
        if len(results) >= limit:
            break
    return results