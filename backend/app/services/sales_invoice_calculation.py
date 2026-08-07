"""Backend-authoritative money calculation for sales invoices.

All monetary amounts are persisted as integer øre. Quantity is handled as
Decimal with explicit rounding; binary floats are never used for money.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Any

SUPPORTED_VAT_RATES = frozenset({0, 12, 15, 25})

MAX_QUANTITY = Decimal("999999")
MAX_UNIT_PRICE_ORE = 100_000_000_00  # 100 million NOK per unit


class InvoiceCalculationError(ValueError):
    """Raised when invoice line input cannot be used for calculation."""


def parse_quantity(value: Any) -> Decimal:
    """Parse a quantity input into a positive Decimal with at most 4 decimals."""
    if isinstance(value, Decimal):
        quantity = value
    else:
        raw = str(value or "").strip().replace(",", ".")
        if not raw:
            raise InvoiceCalculationError("Antall må oppgis.")
        try:
            quantity = Decimal(raw)
        except InvalidOperation as exc:
            raise InvoiceCalculationError("Antall må være et gyldig tall.") from exc

    if quantity <= 0:
        raise InvoiceCalculationError("Antall må være større enn null.")
    if quantity > MAX_QUANTITY:
        raise InvoiceCalculationError("Antall er for stort.")
    return quantity.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP).normalize()


def parse_unit_price_ore(value: Any) -> int:
    """Parse a unit price (øre) into a non-negative integer."""
    try:
        price = int(value)
    except (TypeError, ValueError) as exc:
        raise InvoiceCalculationError("Pris må oppgis i øre.") from exc
    if price < 0:
        raise InvoiceCalculationError("Pris kan ikke være negativ.")
    if price > MAX_UNIT_PRICE_ORE:
        raise InvoiceCalculationError("Pris er for høy.")
    return price


def parse_vat_rate(value: Any) -> int:
    """Validate that the VAT rate is one of the supported rates."""
    try:
        rate = int(value)
    except (TypeError, ValueError) as exc:
        raise InvoiceCalculationError("MVA-sats må oppgis.") from exc
    if rate not in SUPPORTED_VAT_RATES:
        raise InvoiceCalculationError("MVA-satsen er ikke støttet. Bruk 0, 12, 15 eller 25.")
    return rate


def calculate_line(
    *,
    quantity: Any,
    unit_price_ex_vat_ore: Any,
    vat_rate: Any,
) -> dict[str, Any]:
    """Calculate net, VAT and total for one invoice line.

    Returns a dict with parsed inputs and computed integer øre amounts.
    """
    parsed_quantity = parse_quantity(quantity)
    price_ore = parse_unit_price_ore(unit_price_ex_vat_ore)
    rate = parse_vat_rate(vat_rate)

    line_net_ore = int((parsed_quantity * Decimal(price_ore)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    line_vat_ore = int((Decimal(line_net_ore) * Decimal(rate) / Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    line_total_ore = line_net_ore + line_vat_ore

    return {
        "quantity": str(parsed_quantity),
        "unit_price_ex_vat_ore": price_ore,
        "vat_rate": rate,
        "line_net_ore": line_net_ore,
        "line_vat_ore": line_vat_ore,
        "line_total_ore": line_total_ore,
    }


def calculate_totals(lines: list[dict[str, Any]]) -> dict[str, int]:
    """Compute invoice totals from already-calculated lines."""
    subtotal_ore = sum(int(line.get("line_net_ore") or 0) for line in lines)
    vat_total_ore = sum(int(line.get("line_vat_ore") or 0) for line in lines)
    total_ore = subtotal_ore + vat_total_ore
    return {
        "subtotal_ore": subtotal_ore,
        "vat_total_ore": vat_total_ore,
        "total_ore": total_ore,
    }


def calculate_invoice(lines: list[dict[str, Any]]) -> dict[str, Any]:
    """Backend-authoritative calculation for a set of invoice lines.

    Accepts lines with raw inputs (quantity, unit_price_ex_vat_ore, vat_rate)
    and returns the same lines enriched with computed integer øre amounts,
    plus invoice totals. This is the single source of truth for amounts.
    """
    calculated_lines: list[dict[str, Any]] = []
    for line in lines:
        computed = calculate_line(
            quantity=line.get("quantity"),
            unit_price_ex_vat_ore=line.get("unit_price_ex_vat_ore"),
            vat_rate=line.get("vat_rate"),
        )
        enriched = dict(line)
        enriched.update(computed)
        calculated_lines.append(enriched)
    totals = calculate_totals(calculated_lines)
    return {
        "lines": calculated_lines,
        **totals,
    }


def format_nok(ore: int) -> str:
    """Format integer øre as a Norwegian-style NOK string, e.g. 312500 -> '3 125,00'."""
    negative = ore < 0
    kroner = abs(ore) // 100
    remainder = abs(ore) % 100
    kroner_str = f"{kroner:,}".replace(",", " ")
    result = f"{kroner_str},{remainder:02d}"
    return f"-{result}" if negative else result


def format_nok_with_currency(ore: int) -> str:
    return f"{format_nok(ore)} kr"