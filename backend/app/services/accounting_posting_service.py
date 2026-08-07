"""Source-document to journal mapping for Barebonde.

Maps vouchers, sales invoices, payments and corrections to balanced
JournalEntry lines via :mod:`app.services.journal_service`.

All amounts are handled as integer ore. Floats from legacy voucher fields are
converted with Decimal/ROUND_HALF_UP.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from app.services.accounting_catalog import (
    account_exists,
    get_account,
    get_vat_code,
    is_income_account,
    normalize_legacy_vat_code,
)
from app.services import journal_service
from app.services.journal_service import JournalValidationError, to_ore

DEFAULT_BANK_ACCOUNT = "1920"
DEFAULT_SUPPLIER_DEBT_ACCOUNT = "2400"
DEFAULT_REVENUE_ACCOUNT = "3000"
DEFAULT_AR_ACCOUNT = "1500"
INPUT_VAT_ACCOUNT = "2710"
OUTPUT_VAT_ACCOUNT = "2700"


class PostingError(ValueError):
    """Raised when a source document cannot be posted to the journal."""


def _ore(value: Any) -> int:
    return to_ore(value)


def _resolve_vat_code(raw_code: Optional[str], direction: str) -> Optional[str]:
    """Resolve a VAT code to the internal catalog, or None if ambiguous."""
    if not raw_code:
        return None
    if get_vat_code(raw_code):
        return str(raw_code).strip()
    return normalize_legacy_vat_code(raw_code, direction=direction)


def _vat_split_ore(
    *,
    amount: Any,
    amount_excluding_vat: Any,
    vat_amount: Any,
    vat_code: Optional[str],
) -> tuple[int, int]:
    """Return (net_ore, vat_ore) using user-confirmed values when consistent.

    Raises PostingError if confirmed values are inconsistent.
    """
    total_ore = _ore(amount)
    net_confirmed = amount_excluding_vat is not None
    vat_confirmed = vat_amount is not None

    if net_confirmed and vat_confirmed:
        net_ore = _ore(amount_excluding_vat)
        vat_ore = _ore(vat_amount)
        if net_ore + vat_ore != total_ore:
            raise PostingError(
                "Beløpene stemmer ikke overens: netto + MVA er ikke lik totalbeløpet. "
                "Kontroller verdiene før bokføring."
            )
        return net_ore, vat_ore

    vat_meta = get_vat_code(vat_code) if vat_code else None
    rate = Decimal(vat_meta["rate"]) / Decimal(100) if vat_meta and vat_meta.get("rate") else Decimal(0)

    if net_confirmed:
        net_ore = _ore(amount_excluding_vat)
        vat_ore = total_ore - net_ore
        return net_ore, vat_ore
    if vat_confirmed:
        vat_ore = _ore(vat_amount)
        return total_ore - vat_ore, vat_ore

    if rate == 0:
        return total_ore, 0

    # Derive net/VAT from total and known rate with Decimal arithmetic.
    net_dec = (Decimal(total_ore) / (Decimal(1) + rate)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    net_ore = int(net_dec)
    vat_ore = total_ore - net_ore
    return net_ore, vat_ore


# ---------------------------------------------------------------------------
# Voucher booking
# ---------------------------------------------------------------------------

def build_voucher_lines(
    *,
    transaction_type: str,
    account_code: str,
    counter_account_code: Optional[str],
    vat_code: Optional[str],
    amount: Any,
    amount_excluding_vat: Any = None,
    vat_amount: Any = None,
    vat_registered: bool = True,
    description: str = "",
) -> list[dict[str, Any]]:
    """Build balanced journal lines for a voucher booking."""
    if transaction_type not in {"income", "expense"}:
        raise PostingError("transaction_type må være income eller expense")
    if not account_exists(account_code):
        raise PostingError(f"Ukjent konto: {account_code}")

    counter = (counter_account_code or "").strip()
    if not counter:
        raise PostingError("Motkonto er påkrevd for dobbel bokføring.")
    if not account_exists(counter):
        raise PostingError(f"Ukjent motkonto: {counter}")

    total_ore = _ore(amount)
    if total_ore <= 0:
        raise PostingError("Beløp må være større enn null.")

    direction = "input" if transaction_type == "expense" else "output"
    resolved_vat = _resolve_vat_code(vat_code, direction) if vat_registered else None

    net_ore = total_ore
    vat_ore = 0
    if vat_registered and resolved_vat and resolved_vat != "none":
        net_ore, vat_ore = _vat_split_ore(
            amount=amount,
            amount_excluding_vat=amount_excluding_vat,
            vat_amount=vat_amount,
            vat_code=resolved_vat,
        )
        if vat_ore < 0 or net_ore < 0:
            raise PostingError("Beløpene gir negative verdier. Kontroller verdiene.")
        if vat_ore == 0:
            resolved_vat = "none"

    lines: list[dict[str, Any]] = []
    if transaction_type == "expense":
        lines.append(
            {"account_code": account_code, "debit_ore": net_ore, "credit_ore": 0, "description": description, "vat_code": "none"}
        )
        if vat_ore > 0 and resolved_vat and resolved_vat != "none":
            lines.append(
                {
                    "account_code": INPUT_VAT_ACCOUNT,
                    "debit_ore": vat_ore,
                    "credit_ore": 0,
                    "description": "Inngående MVA",
                    "vat_code": resolved_vat,
                    "vat_amount_ore": vat_ore,
                }
            )
        lines.append(
            {"account_code": counter, "debit_ore": 0, "credit_ore": total_ore, "description": description, "vat_code": "none"}
        )
    else:
        lines.append(
            {"account_code": counter, "debit_ore": total_ore, "credit_ore": 0, "description": description, "vat_code": "none"}
        )
        lines.append(
            {"account_code": account_code, "debit_ore": 0, "credit_ore": net_ore, "description": description, "vat_code": "none"}
        )
        if vat_ore > 0 and resolved_vat and resolved_vat != "none":
            lines.append(
                {
                    "account_code": OUTPUT_VAT_ACCOUNT,
                    "debit_ore": 0,
                    "credit_ore": vat_ore,
                    "description": "Utgående MVA",
                    "vat_code": resolved_vat,
                    "vat_amount_ore": vat_ore,
                }
            )

    # Remove accidental zero lines (e.g. net == 0).
    lines = [line for line in lines if line["debit_ore"] > 0 or line["credit_ore"] > 0]
    journal_service.validate_lines(lines)
    return lines


def post_voucher_booking(
    *,
    farm_id: str,
    voucher: dict[str, Any],
    transaction_type: str,
    account_code: str,
    counter_account_code: Optional[str],
    vat_code: Optional[str],
    amount: Any,
    amount_excluding_vat: Any = None,
    vat_amount: Any = None,
    description: str = "",
    posting_date: Optional[str] = None,
    user_id: str,
    vat_registered: bool = True,
) -> dict[str, Any]:
    voucher_id = str(voucher["id"])
    source_key = f"voucher:{voucher_id}:booking"
    document_type = str(voucher.get("document_type") or "invoice").lower()

    if not counter_account_code:
        if document_type == "receipt":
            counter_account_code = DEFAULT_BANK_ACCOUNT
        elif document_type == "invoice":
            counter_account_code = DEFAULT_SUPPLIER_DEBT_ACCOUNT
        else:
            raise PostingError(
                "Bilags typen er tvetydig. Velg motkonto (Leverandørgjeld eller Bank) eksplisitt."
            )

    lines = build_voucher_lines(
        transaction_type=transaction_type,
        account_code=account_code,
        counter_account_code=counter_account_code,
        vat_code=vat_code,
        amount=amount,
        amount_excluding_vat=amount_excluding_vat,
        vat_amount=vat_amount,
        vat_registered=vat_registered,
        description=description,
    )

    return journal_service.post_entry(
        farm_id=farm_id,
        posting_date=posting_date or str(voucher.get("voucher_date") or date.today().isoformat()),
        document_date=voucher.get("voucher_date"),
        source_type=journal_service.SOURCE_TYPE_VOUCHER,
        source_id=voucher_id,
        source_event="booking",
        source_key=source_key,
        description=description or str(voucher.get("description") or "Bilag"),
        lines=lines,
        user_id=user_id,
        source_revision=1,
        source_snapshot={
            "document_number": voucher.get("invoice_number"),
            "counterparty_name": voucher.get("supplier_name"),
            "accounting_mapping_version": 1,
        },
    )


# ---------------------------------------------------------------------------
# Voucher correction
# ---------------------------------------------------------------------------

def effective_voucher_entries(farm_id: str, voucher_id: str) -> list[dict[str, Any]]:
    """Return all journal entries for a voucher ordered by revision."""
    entries = journal_service.list_entries(
        farm_id, source_type=journal_service.SOURCE_TYPE_VOUCHER, source_id=voucher_id, limit=100
    )
    return sorted(entries, key=lambda entry: int(entry.get("source_revision") or 1))


def post_voucher_correction(
    *,
    farm_id: str,
    voucher: dict[str, Any],
    transaction_type: str,
    account_code: str,
    counter_account_code: Optional[str],
    vat_code: Optional[str],
    amount: Any,
    amount_excluding_vat: Any = None,
    vat_amount: Any = None,
    description: str = "",
    correction_date: Optional[str] = None,
    reason: str,
    user_id: str,
    vat_registered: bool = True,
) -> dict[str, Any]:
    """Post a correction entry that reverses current effect and posts the new one."""
    voucher_id = str(voucher["id"])
    prior_entries = effective_voucher_entries(farm_id, voucher_id)
    booking_entries = [entry for entry in prior_entries if entry.get("source_event") in {"booking", "correction"}]
    if not booking_entries:
        raise PostingError("Bilaget har ingen bokføring å korrigere.")

    current = booking_entries[-1]
    current_revision = int(current.get("source_revision") or 1)
    new_revision = current_revision + 1

    # Reverse the current accounting effect.
    reversal_lines: list[dict[str, Any]] = []
    for line in current.get("lines", []):
        reversal_lines.append(
            {
                "account_code": line["account_code"],
                "debit_ore": int(line.get("credit_ore") or 0),
                "credit_ore": int(line.get("debit_ore") or 0),
                "description": f"Revers: {line.get('description') or ''}".strip(),
                "vat_code": line.get("vat_code") or "none",
                "vat_amount_ore": int(line.get("vat_amount_ore") or 0),
            }
        )

    document_type = str(voucher.get("document_type") or "invoice").lower()
    if not counter_account_code:
        counter_account_code = DEFAULT_BANK_ACCOUNT if document_type == "receipt" else DEFAULT_SUPPLIER_DEBT_ACCOUNT

    corrected_lines = build_voucher_lines(
        transaction_type=transaction_type,
        account_code=account_code,
        counter_account_code=counter_account_code,
        vat_code=vat_code,
        amount=amount,
        amount_excluding_vat=amount_excluding_vat,
        vat_amount=vat_amount,
        vat_registered=vat_registered,
        description=description,
    )

    combined = reversal_lines + corrected_lines
    journal_service.validate_lines(combined)

    source_key = f"voucher:{voucher_id}:correction:{new_revision}"
    return journal_service.post_entry(
        farm_id=farm_id,
        posting_date=correction_date or date.today().isoformat(),
        document_date=voucher.get("voucher_date"),
        source_type=journal_service.SOURCE_TYPE_VOUCHER,
        source_id=voucher_id,
        source_event="correction",
        source_key=source_key,
        description=f"Korrigering: {description or voucher.get('description') or 'Bilag'}",
        lines=combined,
        user_id=user_id,
        correction_of=current.get("id"),
        correction_reason=reason,
        source_revision=new_revision,
        source_snapshot={
            "document_number": voucher.get("invoice_number"),
            "counterparty_name": voucher.get("supplier_name"),
            "accounting_mapping_version": 1,
        },
    )


# ---------------------------------------------------------------------------
# Sales invoice issue + payment
# ---------------------------------------------------------------------------

def build_sales_invoice_issue_lines(invoice: dict[str, Any]) -> list[dict[str, Any]]:
    """Build issue lines: debit AR total, credit revenue net per rate, credit output VAT."""
    total_ore = int(invoice.get("total_ore") or 0)
    subtotal_ore = int(invoice.get("subtotal_ore") or 0)
    vat_total_ore = int(invoice.get("vat_total_ore") or 0)
    if total_ore <= 0:
        raise PostingError("Fakturaen har ikke noe beløp å bokføre.")
    if subtotal_ore + vat_total_ore != total_ore:
        raise PostingError("Fakturaens summer stemmer ikke (netto + MVA != total).")

    seller = invoice.get("seller_snapshot") or {}
    vat_registered = seller.get("vat_registered") not in {False, "no", "false"}
    if not vat_registered and vat_total_ore > 0:
        raise PostingError(
            "Gården er ikke MVA-registrert, men fakturaen har MVA. "
            "Bokføringen krever gjennomgang."
        )

    # Group revenue by line account_code and VAT rate.
    revenue_by_account: dict[str, int] = {}
    vat_by_rate: dict[int, int] = {}
    legacy_default_used = False
    for line in invoice.get("lines", []):
        line_total = int(line.get("total_ore") or 0)
        line_net = int(line.get("subtotal_ore") or (line_total - int(line.get("vat_ore") or 0)))
        line_vat = int(line.get("vat_ore") or 0)
        account_code = line.get("account_code") or DEFAULT_REVENUE_ACCOUNT
        if not line.get("account_code"):
            legacy_default_used = True
        if not is_income_account(account_code):
            raise PostingError(f"Linje bruker ikke en inntektskonto: {account_code}")
        revenue_by_account[account_code] = revenue_by_account.get(account_code, 0) + line_net
        if line_vat:
            rate = int(line.get("vat_rate") or 25)
            vat_by_rate[rate] = vat_by_rate.get(rate, 0) + line_vat

    lines: list[dict[str, Any]] = [
        {
            "account_code": DEFAULT_AR_ACCOUNT,
            "debit_ore": total_ore,
            "credit_ore": 0,
            "description": "Kundefordring",
            "vat_code": "none",
        }
    ]
    for account_code, net_ore in revenue_by_account.items():
        if net_ore <= 0:
            continue
        lines.append(
            {
                "account_code": account_code,
                "debit_ore": 0,
                "credit_ore": net_ore,
                "description": "Salgsinntekt",
                "vat_code": "none",
            }
        )
    for rate, vat_ore in vat_by_rate.items():
        if vat_ore <= 0:
            continue
        code = f"output_{rate}" if get_vat_code(f"output_{rate}") else "output_25"
        lines.append(
            {
                "account_code": OUTPUT_VAT_ACCOUNT,
                "debit_ore": 0,
                "credit_ore": vat_ore,
                "description": "Utgående MVA",
                "vat_code": code,
                "vat_amount_ore": vat_ore,
            }
        )

    journal_service.validate_lines(lines)
    return lines


def post_sales_invoice_issue(
    *,
    farm_id: str,
    invoice: dict[str, Any],
    user_id: str,
) -> dict[str, Any]:
    invoice_id = str(invoice["id"])
    lines = build_sales_invoice_issue_lines(invoice)
    return journal_service.post_entry(
        farm_id=farm_id,
        posting_date=str(invoice.get("issued_at") or invoice.get("issue_date") or date.today().isoformat())[:10],
        document_date=str(invoice.get("issue_date") or date.today().isoformat())[:10],
        source_type=journal_service.SOURCE_TYPE_SALES_INVOICE,
        source_id=invoice_id,
        source_event="issue",
        source_key=f"sales_invoice:{invoice_id}:issue",
        description=f"Salgsfaktura {invoice.get('invoice_number') or invoice_id}",
        lines=lines,
        user_id=user_id,
        source_snapshot={
            "document_number": invoice.get("invoice_number"),
            "counterparty_name": (invoice.get("customer") or {}).get("name"),
            "accounting_mapping_version": 1,
        },
    )


def post_sales_invoice_payment(
    *,
    farm_id: str,
    invoice: dict[str, Any],
    user_id: str,
    bank_account_code: str = DEFAULT_BANK_ACCOUNT,
    payment_date: Optional[str] = None,
) -> dict[str, Any]:
    invoice_id = str(invoice["id"])
    total_ore = int(invoice.get("total_ore") or 0)
    if total_ore <= 0:
        raise PostingError("Fakturaen har ikke noe beløp å bokføre.")
    if not account_exists(bank_account_code):
        raise PostingError(f"Ukjent bankkonto: {bank_account_code}")

    lines = [
        {
            "account_code": bank_account_code,
            "debit_ore": total_ore,
            "credit_ore": 0,
            "description": "Innbetaling",
            "vat_code": "none",
        },
        {
            "account_code": DEFAULT_AR_ACCOUNT,
            "debit_ore": 0,
            "credit_ore": total_ore,
            "description": "Kundefordring innfridd",
            "vat_code": "none",
        },
    ]
    return journal_service.post_entry(
        farm_id=farm_id,
        posting_date=payment_date or date.today().isoformat(),
        document_date=payment_date or date.today().isoformat(),
        source_type=journal_service.SOURCE_TYPE_SALES_INVOICE,
        source_id=invoice_id,
        source_event="payment",
        source_key=f"sales_invoice:{invoice_id}:payment",
        description=f"Innbetaling faktura {invoice.get('invoice_number') or invoice_id}",
        lines=lines,
        user_id=user_id,
        source_snapshot={
            "document_number": invoice.get("invoice_number"),
            "counterparty_name": (invoice.get("customer") or {}).get("name"),
            "accounting_mapping_version": 1,
        },
    )