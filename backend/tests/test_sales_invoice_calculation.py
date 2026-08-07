"""Targeted tests for sales invoice calculation engine."""
from decimal import Decimal

import pytest

from app.services.sales_invoice_calculation import (
    calculate_invoice_totals,
    calculate_line,
    validate_lines,
)


def make_line(description="Test", quantity="1", unit="stk", unit_price_ex_vat_ore=100000, vat_rate=25):
    return {
        "description": description,
        "quantity": quantity,
        "unit": unit,
        "unit_price_ex_vat_ore": unit_price_ex_vat_ore,
        "vat_rate": vat_rate,
    }


class TestCalculateLine:
    def test_basic_line(self):
        line = make_line(quantity="2.5", unit_price_ex_vat_ore=100000, vat_rate=25)
        result = calculate_line(line)
        assert result["line_net_ore"] == 250000
        assert result["line_vat_ore"] == 62500
        assert result["line_total_ore"] == 312500

    def test_zero_vat(self):
        line = make_line(quantity="1", unit_price_ex_vat_ore=50000, vat_rate=0)
        result = calculate_line(line)
        assert result["line_net_ore"] == 50000
        assert result["line_vat_ore"] == 0
        assert result["line_total_ore"] == 50000

    def test_rounding(self):
        # 1.33 * 9999 = 13298.67 -> rounds to 13299
        line = make_line(quantity="1.33", unit_price_ex_vat_ore=9999, vat_rate=25)
        result = calculate_line(line)
        assert result["line_net_ore"] == 13299
        assert result["line_vat_ore"] == 3325  # 13299 * 0.25 = 3324.75 -> 3325
        assert result["line_total_ore"] == 16624

    def test_fractional_quantity(self):
        line = make_line(quantity="0.5", unit_price_ex_vat_ore=1000, vat_rate=15)
        result = calculate_line(line)
        assert result["line_net_ore"] == 500
        assert result["line_vat_ore"] == 75
        assert result["line_total_ore"] == 575


class TestCalculateTotals:
    def test_multiple_lines(self):
        lines = [
            make_line(quantity="2", unit_price_ex_vat_ore=100000, vat_rate=25),
            make_line(quantity="1", unit_price_ex_vat_ore=50000, vat_rate=12),
        ]
        totals = calculate_invoice_totals(lines)
        assert totals["subtotal_ore"] == 250000
        assert totals["vat_total_ore"] == 56000
        assert totals["total_ore"] == 306000

    def test_empty_lines(self):
        totals = calculate_invoice_totals([])
        assert totals["subtotal_ore"] == 0
        assert totals["vat_total_ore"] == 0
        assert totals["total_ore"] == 0


class TestValidateLines:
    def test_valid_lines(self):
        lines = [make_line()]
        errors = validate_lines(lines)
        assert errors == []

    def test_empty_lines_rejected(self):
        errors = validate_lines([])
        assert any("minst" in e.lower() for e in errors)

    def test_empty_description_rejected(self):
        lines = [make_line(description="")]
        errors = validate_lines(lines)
        assert any("beskrivelse" in e.lower() for e in errors)

    def test_zero_quantity_rejected(self):
        lines = [make_line(quantity="0")]
        errors = validate_lines(lines)
        assert any("antall" in e.lower() for e in errors)

    def test_negative_quantity_rejected(self):
        lines = [make_line(quantity="-1")]
        errors = validate_lines(lines)
        assert any("antall" in e.lower() for e in errors)

    def test_negative_price_rejected(self):
        lines = [make_line(unit_price_ex_vat_ore=-100)]
        errors = validate_lines(lines)
        assert any("pris" in e.lower() for e in errors)

    def test_unsupported_vat_rate_rejected(self):
        lines = [make_line(vat_rate=33)]
        errors = validate_lines(lines)
        assert any("mva" in e.lower() for e in errors)

    def test_invalid_quantity_string_rejected(self):
        lines = [make_line(quantity="abc")]
        errors = validate_lines(lines)
        assert any("antall" in e.lower() for e in errors)