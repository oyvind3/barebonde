"""Standalone verification for sales_invoice_calculation (no pytest required)."""
import sys
sys.path.insert(0, ".")

from app.services.sales_invoice_calculation import (
    InvoiceCalculationError,
    calculate_line,
    calculate_totals,
    format_nok,
    format_nok_with_currency,
)


def main():
    # Basic line: 2.5 x 1000.00 ex VAT @ 25%
    r = calculate_line(quantity="2.5", unit_price_ex_vat_ore=100000, vat_rate=25)
    assert r["line_net_ore"] == 250000, f"net={r['line_net_ore']}"
    assert r["line_vat_ore"] == 62500, f"vat={r['line_vat_ore']}"
    assert r["line_total_ore"] == 312500, f"total={r['line_total_ore']}"

    # Zero VAT
    r = calculate_line(quantity="1", unit_price_ex_vat_ore=50000, vat_rate=0)
    assert r["line_net_ore"] == 50000
    assert r["line_vat_ore"] == 0
    assert r["line_total_ore"] == 50000

    # Rounding: 1.33 * 99.99 kr = 13298.67 ore -> 13299; vat 3324.75 -> 3325
    r = calculate_line(quantity="1.33", unit_price_ex_vat_ore=9999, vat_rate=25)
    assert r["line_net_ore"] == 13299, f"net={r['line_net_ore']}"
    assert r["line_vat_ore"] == 3325, f"vat={r['line_vat_ore']}"
    assert r["line_total_ore"] == 16624, f"total={r['line_total_ore']}"

    # Fractional quantity with 15% VAT
    r = calculate_line(quantity="0.5", unit_price_ex_vat_ore=1000, vat_rate=15)
    assert r["line_net_ore"] == 500
    assert r["line_vat_ore"] == 75
    assert r["line_total_ore"] == 575

    # Norwegian decimal comma input
    r = calculate_line(quantity="2,5", unit_price_ex_vat_ore=100000, vat_rate=25)
    assert r["line_net_ore"] == 250000

    # Totals across multiple lines
    line_a = calculate_line(quantity="2", unit_price_ex_vat_ore=100000, vat_rate=25)
    line_b = calculate_line(quantity="1", unit_price_ex_vat_ore=50000, vat_rate=12)
    t = calculate_totals([line_a, line_b])
    assert t["subtotal_ore"] == 250000, f"sub={t['subtotal_ore']}"
    assert t["vat_total_ore"] == 56000, f"vat={t['vat_total_ore']}"
    assert t["total_ore"] == 306000, f"total={t['total_ore']}"

    # Empty lines
    t = calculate_totals([])
    assert t["subtotal_ore"] == 0 and t["vat_total_ore"] == 0 and t["total_ore"] == 0

    # Validation errors
    for bad_kwargs in [
        {"quantity": "0", "unit_price_ex_vat_ore": 100, "vat_rate": 25},
        {"quantity": "-1", "unit_price_ex_vat_ore": 100, "vat_rate": 25},
        {"quantity": "abc", "unit_price_ex_vat_ore": 100, "vat_rate": 25},
        {"quantity": "1", "unit_price_ex_vat_ore": -100, "vat_rate": 25},
        {"quantity": "1", "unit_price_ex_vat_ore": 100, "vat_rate": 33},
    ]:
        try:
            calculate_line(**bad_kwargs)
            raise AssertionError(f"expected error for {bad_kwargs}")
        except InvoiceCalculationError:
            pass

    # Formatting
    assert format_nok(312500) == "3 125,00", f"format={format_nok(312500)}"
    assert format_nok(99) == "0,99"
    assert format_nok_with_currency(312500) == "3 125,00 kr"

    print("ALL CALCULATION CHECKS PASSED")


if __name__ == "__main__":
    main()