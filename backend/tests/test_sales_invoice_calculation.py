"""Targeted tests for the sales invoice calculation engine."""
import pytest

from app.services.sales_invoice_calculation import (
    InvoiceCalculationError,
    calculate_invoice,
    calculate_line,
    calculate_totals,
    format_nok,
    format_nok_with_currency,
)


def make_line(description="Test", quantity="1", unit="stk", unit_price_ex_vat_ore=100000, vat_rate=25):
    return {
        "id": "line:test",
        "description": description,
        "quantity": quantity,
        "unit": unit,
        "unit_price_ex_vat_ore": unit_price_ex_vat_ore,
        "vat_rate": vat_rate,
    }


class TestCalculateLine:
    def test_basic_line(self):
        result = calculate_line(quantity="2.5", unit_price_ex_vat_ore=100000, vat_rate=25)
        assert result["line_net_ore"] == 250000
        assert result["line_vat_ore"] == 62500
        assert result["line_total_ore"] == 312500

    def test_zero_vat(self):
        result = calculate_line(quantity="1", unit_price_ex_vat_ore=50000, vat_rate=0)
        assert result["line_net_ore"] == 50000
        assert result["line_vat_ore"] == 0
        assert result["line_total_ore"] == 50000

    def test_rounding_half_up(self):
        # 1.33 * 99.99 kr = 13298.67 ore -> 13299; VAT 25% = 3324.75 -> 3325
        result = calculate_line(quantity="1.33", unit_price_ex_vat_ore=9999, vat_rate=25)
        assert result["line_net_ore"] == 13299
        assert result["line_vat_ore"] == 3325
        assert result["line_total_ore"] == 16624

    def test_fractional_quantity_15_vat(self):
        result = calculate_line(quantity="0.5", unit_price_ex_vat_ore=1000, vat_rate=15)
        assert result["line_net_ore"] == 500
        assert result["line_vat_ore"] == 75
        assert result["line_total_ore"] == 575

    def test_norwegian_decimal_comma(self):
        result = calculate_line(quantity="2,5", unit_price_ex_vat_ore=100000, vat_rate=25)
        assert result["line_net_ore"] == 250000

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"quantity": "0", "unit_price_ex_vat_ore": 100, "vat_rate": 25},
            {"quantity": "-1", "unit_price_ex_vat_ore": 100, "vat_rate": 25},
            {"quantity": "abc", "unit_price_ex_vat_ore": 100, "vat_rate": 25},
            {"quantity": "", "unit_price_ex_vat_ore": 100, "vat_rate": 25},
            {"quantity": "1", "unit_price_ex_vat_ore": -100, "vat_rate": 25},
            {"quantity": "1", "unit_price_ex_vat_ore": 100, "vat_rate": 33},
            {"quantity": "1", "unit_price_ex_vat_ore": 100, "vat_rate": None},
        ],
    )
    def test_invalid_inputs_raise(self, kwargs):
        with pytest.raises(InvoiceCalculationError):
            calculate_line(**kwargs)


class TestCalculateInvoice:
    def test_totals_across_lines(self):
        lines = [
            make_line(quantity="2", unit_price_ex_vat_ore=100000, vat_rate=25),
            make_line(quantity="1", unit_price_ex_vat_ore=50000, vat_rate=12),
        ]
        result = calculate_invoice(lines)
        assert result["subtotal_ore"] == 250000
        assert result["vat_total_ore"] == 56000
        assert result["total_ore"] == 306000
        assert len(result["lines"]) == 2
        # Lines are enriched with computed amounts
        assert result["lines"][0]["line_total_ore"] == 250000
        assert result["lines"][1]["line_total_ore"] == 56000

    def test_empty_lines(self):
        result = calculate_invoice([])
        assert result["subtotal_ore"] == 0
        assert result["vat_total_ore"] == 0
        assert result["total_ore"] == 0
        assert result["lines"] == []

    def test_line_metadata_preserved(self):
        result = calculate_invoice([make_line(description="Leiekjøring", unit="time")])
        assert result["lines"][0]["description"] == "Leiekjøring"
        assert result["lines"][0]["unit"] == "time"
        assert result["lines"][0]["id"] == "line:test"


class TestCalculateTotals:
    def test_sums_calculated_lines(self):
        line_a = calculate_line(quantity="2", unit_price_ex_vat_ore=100000, vat_rate=25)
        line_b = calculate_line(quantity="1", unit_price_ex_vat_ore=50000, vat_rate=12)
        totals = calculate_totals([line_a, line_b])
        assert totals["subtotal_ore"] == 250000
        assert totals["vat_total_ore"] == 56000
        assert totals["total_ore"] == 306000


class TestFormatNok:
    def test_format(self):
        assert format_nok(312500) == "3 125,00"
        assert format_nok(99) == "0,99"
        assert format_nok(0) == "0,00"
        assert format_nok_with_currency(312500) == "3 125,00 kr"