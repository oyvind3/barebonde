"""Deterministic invoice field extraction service.

This module extracts structured fields from OCR text without using generative AI.
It supports Norwegian formats and prioritizes amounts linked to explicit total labels.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class FieldCandidate:
    """A single candidate value with confidence metadata."""

    value: str
    confidence: float
    source: str  # "ocr", "inferred", "fallback"
    needs_review: bool = True
    label_context: Optional[str] = None


class InvoiceFieldParser:
    """Extract invoice fields from OCR text using deterministic rules."""

    # Norwegian keywords for totals
    TOTAL_KEYWORDS = [
        r"å betale",
        r"aa betale",
        r"til betaling",
        r"totalt",
        r"total",
        r"sum inkl.? mva",
        r"sum inkl.?",
        r"beløp å betale",
        r"belop a betale",
        r"forfaller",
        r"betaling",
        r" Netto",
        r" Totalt",
        r" TOTAL",
        r" SUM",
    ]

    VAT_KEYWORDS = [
        r"mva",
        r"merverdiavgift",
        r"merkesalgsavgift",
        r"vg",
        r"MVA",
        r"MOMS",
    ]

    DATE_KEYWORDS = [
        r"fakturadato",
        r"faktura dato",
        r"dato",
        r"utstedt",
        r"forfallsdato",
        r"forfall",
        r"kjøpsdato",
    ]

    INVOICE_NUMBER_KEYWORDS = [
        r"fakturanr",
        r"fakturanummer",
        r"faktura ?nr\.?",
        r"invoice ?no\.?",
        r"referanse",
        r"ordrenr",
        r"ordre ?nr\.?",
    ]

    ORG_NUMBER_PATTERNS = [
        r"(?:org\.?\s*nr\.?|organisasjonsnummer|foretaksnummer)[\s:]*([0-9]{9})",
        r"(?:Org\.?\s*Nr\.?|Organisasjonsnummer)[\s:]*([0-9]{9})",
    ]

    KID_PATTERNS = [
        r"(?:KID|Kid|kid)[\s:]*([0-9\s]+)",
        r"(?:Referanse|Payment reference)[\s:]*([0-9\s]+)",
    ]

    BANK_ACCOUNT_PATTERNS = [
        r"(?:Bankkonto|Kontonummer|Account number|IBAN)[\s:]*([A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:\d{0,7})?)",
        r"(?:Bankkonto|Kontonr\.?)[\s:]*([0-9]{4}\.?[0-9]{2}\.?[0-9]{5})",
    ]

    def parse_fields(self, text: str) -> dict[str, Any]:
        """Parse all invoice fields from OCR text.

        Returns a dictionary with suggested values and confidence scores.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        normalized = "\n".join(lines)

        return {
            "supplier_name": self._extract_supplier_name(lines),
            "org_number": self._extract_org_number(normalized),
            "invoice_number": self._extract_invoice_number(lines),
            "invoice_date": self._extract_invoice_date(normalized),
            "due_date": self._extract_due_date(normalized),
            "amount_total": self._extract_total_amount(normalized),
            "amount_vat": self._extract_vat_amount(normalized),
            "amount_excl_vat": self._extract_amount_excl_vat(normalized),
            "currency": self._extract_currency(normalized),
            "kid": self._extract_kid(normalized),
            "bank_account": self._extract_bank_account(normalized),
            "description": self._extract_description(lines),
            "text_preview": normalized[:1200],
        }

    def _extract_supplier_name(self, lines: list[str]) -> Optional[FieldCandidate]:
        """Extract supplier name from the first few lines."""
        for line in lines[:10]:
            cleaned = re.sub(r"\s+", " ", line).strip()
            if len(cleaned) < 3:
                continue
            # Skip lines that look like headers or metadata
            if re.search(
                r"org\.nr|faktura|dato|sum|mva|total|kunde|kundeservice|telefon|e-post|www\.",
                cleaned,
                flags=re.IGNORECASE,
            ):
                continue
            # Must contain at least one letter
            if any(ch.isalpha() for ch in cleaned):
                return FieldCandidate(
                    value=cleaned[:80],
                    confidence=0.6,
                    source="ocr",
                    needs_review=True,
                )
        return None

    def _extract_org_number(self, text: str) -> Optional[FieldCandidate]:
        """Extract Norwegian organization number (9 digits)."""
        for pattern in self.ORG_NUMBER_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                org_nr = match.group(1).replace(" ", "")
                if len(org_nr) == 9:
                    return FieldCandidate(
                        value=org_nr,
                        confidence=0.85,
                        source="ocr",
                        needs_review=False,
                        label_context="org.nr",
                    )
        # Fallback: look for standalone 9-digit numbers near "org" context
        standalone_pattern = r"\b(\d{9})\b"
        matches = re.findall(standalone_pattern, text)
        for match in matches:
            # Validate with checksum (simplified)
            if self._validate_org_number(match):
                return FieldCandidate(
                    value=match,
                    confidence=0.5,
                    source="inferred",
                    needs_review=True,
                )
        return None

    def _validate_org_number(self, org_nr: str) -> bool:
        """Validate Norwegian organization number checksum (simplified)."""
        if len(org_nr) != 9 or not org_nr.isdigit():
            return False
        # Simplified validation - just check it's not all zeros or obvious patterns
        if org_nr == "000000000" or org_nr == "123456789":
            return False
        return True

    def _extract_invoice_number(self, lines: list[str]) -> Optional[FieldCandidate]:
        """Extract invoice number."""
        text = "\n".join(lines)
        for keyword in self.INVOICE_NUMBER_KEYWORDS:
            pattern = rf"{keyword}[\s:.]*([A-Za-z0-9\-]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if value and len(value) <= 30:
                    return FieldCandidate(
                        value=value,
                        confidence=0.8,
                        source="ocr",
                        needs_review=False,
                        label_context="fakturanr",
                    )
        return None

    def _extract_invoice_date(self, text: str) -> Optional[FieldCandidate]:
        """Extract invoice date."""
        # Look for explicit invoice date labels first
        for keyword in self.DATE_KEYWORDS:
            if "forfall" in keyword.lower():
                continue  # Skip due date keywords here
            pattern = rf"{keyword}[\s:.]*(\d{{2}}[.\-/]\d{{2}}[.\-/]\d{{2,4}}|\d{{4}}[\-]\d{{2}}[\-]\d{{2}})"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                parsed = self._parse_date(date_str)
                if parsed:
                    return FieldCandidate(
                        value=parsed.isoformat(),
                        confidence=0.85,
                        source="ocr",
                        needs_review=False,
                        label_context="fakturadato",
                    )

        # Fallback: find any date in the text
        return self._find_any_date(text)

    def _extract_due_date(self, text: str) -> Optional[FieldCandidate]:
        """Extract due date (forfallsdato)."""
        due_keywords = [r"forfallsdato", r"forfall", r"forfaller", r"betalingsfrist"]
        for keyword in due_keywords:
            pattern = rf"{keyword}[\s:.]*(\d{{2}}[.\-/]\d{{2}}[.\-/]\d{{2,4}}|\d{{4}}[\-]\d{{2}}[\-]\d{{2}})"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                parsed = self._parse_date(date_str)
                if parsed:
                    return FieldCandidate(
                        value=parsed.isoformat(),
                        confidence=0.85,
                        source="ocr",
                        needs_review=False,
                        label_context="forfallsdato",
                    )
        return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string in various Norwegian formats."""
        formats = [
            "%Y-%m-%d",
            "%d.%m.%Y",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d.%m.%y",
            "%d/%m/%y",
        ]
        date_str = date_str.strip()
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def _find_any_date(self, text: str) -> Optional[FieldCandidate]:
        """Find any date in text as fallback."""
        patterns = [
            r"\b(\d{4}-\d{2}-\d{2})\b",
            r"\b(\d{2}\.\d{2}\.\d{4})\b",
            r"\b(\d{2}/\d{2}/\d{4})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                parsed = self._parse_date(date_str)
                if parsed:
                    return FieldCandidate(
                        value=parsed.isoformat(),
                        confidence=0.5,
                        source="inferred",
                        needs_review=True,
                    )
        return None

    def _extract_total_amount(self, text: str) -> Optional[FieldCandidate]:
        """Extract total amount including VAT.

        Prioritizes amounts linked to explicit total/ payment labels.
        Does NOT simply pick the largest amount.
        """
        candidates: list[tuple[float, float, str]] = []  # (amount, confidence, context)

        # Look for amounts near total keywords
        for keyword in self.TOTAL_KEYWORDS:
            # Match patterns like "Total: 1 234,56" or "Sum kr 500"
            pattern = rf"{keyword}[\s:.]*NOK[\s]*([0-9][0-9\s.,]*)|{keyword}[\s:.]*kr[\s]*([0-9][0-9\s.,]*)|{keyword}[\s:.]*([0-9][0-9\s.,]*)"
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Get the matched group that contains the number
                value = match.group(1) or match.group(2) or match.group(3) or ""
                if value:
                    parsed = self._parse_amount(value.strip())
                    if parsed is not None and parsed > 0:
                        context = match.group(0)[:50]
                        candidates.append((parsed, 0.9, context))

        # Also look for amounts on lines containing "kr" or currency markers
        lines = text.split("\n")
        for line in lines:
            if re.search(r"kr\s*[0-9]", line, re.IGNORECASE):
                amount_match = re.search(r"kr\s*([0-9][0-9\s.,]*)", line, re.IGNORECASE)
                if amount_match:
                    parsed = self._parse_amount(amount_match.group(1))
                    if parsed is not None and parsed > 0:
                        # Lower confidence for unlabeled amounts
                        candidates.append((parsed, 0.4, line[:50]))

        if not candidates:
            # Last resort: find all amounts in text
            all_amounts = self._find_all_amounts(text)
            for amount in all_amounts[:3]:
                candidates.append((amount, 0.2, ""))

        if not candidates:
            return None

        # Sort by confidence first, then by amount (prefer higher confidence over amount size)
        candidates.sort(key=lambda x: (-x[1], -x[0]))

        # Return the highest confidence candidate
        best = candidates[0]
        return FieldCandidate(
            value=str(best[0]),
            confidence=best[1],
            source="ocr" if best[1] > 0.5 else "inferred",
            needs_review=best[1] < 0.7,
            label_context=best[2] if best[2] else None,
        )

    def _extract_vat_amount(self, text: str) -> Optional[FieldCandidate]:
        """Extract VAT amount."""
        for keyword in self.VAT_KEYWORDS:
            pattern = rf"{keyword}[\s:.]*([0-9][0-9\s.,]*)|(?:[0-9][0-9\s.,]*)\s*{keyword}"
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                value = match.group(1) or match.group(0).split()[0]
                if value:
                    parsed = self._parse_amount(value.strip())
                    if parsed is not None and parsed > 0:
                        # Check if this looks like a VAT amount (typically smaller than total)
                        return FieldCandidate(
                            value=str(parsed),
                            confidence=0.7,
                            source="ocr",
                            needs_review=True,
                            label_context="mva",
                        )
        return None

    def _extract_amount_excl_vat(self, text: str) -> Optional[FieldCandidate]:
        """Extract amount excluding VAT if it can be derived safely."""
        total = self._extract_total_amount(text)
        vat = self._extract_vat_amount(text)
        if total and vat:
            try:
                total_val = float(total.value)
                vat_val = float(vat.value)
                if total_val > vat_val:
                    excl_vat = total_val - vat_val
                    return FieldCandidate(
                        value=str(excl_vat),
                        confidence=0.6,
                        source="inferred",
                        needs_review=True,
                        label_context="ekskl. mva",
                    )
            except (ValueError, TypeError):
                pass
        return None

    def _extract_currency(self, text: str) -> Optional[FieldCandidate]:
        """Extract currency code."""
        currency_patterns = [
            r"\b(NOK|nok|NOk)\b",
            r"\b(EUR|eur|Euro|EURO)\b",
            r"\b(USD|usd|Usd|Dollar)\b",
            r"\b(SEK|sek|Sek)\b",
            r"\b(DKK|dkk|Dkk)\b",
        ]
        for pattern in currency_patterns:
            match = re.search(pattern, text)
            if match:
                currency = match.group(1).upper()
                if currency == "NOK":
                    return FieldCandidate(
                        value="NOK",
                        confidence=0.9,
                        source="ocr",
                        needs_review=False,
                    )
                return FieldCandidate(
                    value=currency,
                    confidence=0.8,
                    source="ocr",
                    needs_review=True,
                )
        # Default to NOK
        return FieldCandidate(
            value="NOK",
            confidence=0.5,
            source="fallback",
            needs_review=False,
        )

    def _extract_kid(self, text: str) -> Optional[FieldCandidate]:
        """Extract KID (payment reference) number."""
        for pattern in self.KID_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                kid = match.group(1).replace(" ", "")
                if kid and len(kid) >= 5 and len(kid) <= 25:
                    return FieldCandidate(
                        value=kid,
                        confidence=0.85,
                        source="ocr",
                        needs_review=False,
                        label_context="KID",
                    )
        return None

    def _extract_bank_account(self, text: str) -> Optional[FieldCandidate]:
        """Extract bank account number."""
        for pattern in self.BANK_ACCOUNT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                account = match.group(1).replace(" ", "").replace(".", "")
                if account:
                    return FieldCandidate(
                        value=account,
                        confidence=0.8,
                        source="ocr",
                        needs_review=True,
                        label_context="bankkonto",
                    )
        return None

    def _extract_description(self, lines: list[str]) -> Optional[FieldCandidate]:
        """Extract a short description from the document."""
        # Use supplier name as fallback description
        supplier = self._extract_supplier_name(lines)
        if supplier:
            return FieldCandidate(
                value=supplier.value,
                confidence=supplier.confidence * 0.8,
                source=supplier.source,
                needs_review=True,
            )
        return None

    def _parse_amount(self, value: str) -> Optional[float]:
        """Parse amount string handling Norwegian formats.

        Handles:
        - 1 234,56 (space as thousands, comma as decimal)
        - 1.234,56 (dot as thousands, comma as decimal)
        - 1234.56 (dot as decimal)
        - NOK 1 234,56
        """
        value = value.strip()
        if not value:
            return None

        # Remove currency symbols and spaces around them
        value = re.sub(r"(NOK|nok|kr|KR)\s*", "", value, flags=re.IGNORECASE)
        value = value.strip()

        # Count separators
        comma_count = value.count(",")
        dot_count = value.count(".")
        space_count = value.count(" ")

        try:
            if comma_count == 1 and dot_count >= 1:
                # Format: 1.234,56 - remove dots, replace comma with dot
                normalized = value.replace(".", "").replace(",", ".")
            elif comma_count == 1 and dot_count == 0:
                # Format: 1234,56 or 1 234,56
                normalized = value.replace(" ", "").replace(",", ".")
            elif dot_count > 1:
                # Format: 1.234.567 or 1.234,56 with multiple dots
                # Assume last dot is decimal separator if followed by 2 digits
                if re.search(r"\d{2}$", value):
                    parts = value.rsplit(".", 1)
                    normalized = parts[0].replace(".", "") + "." + parts[1]
                else:
                    normalized = value.replace(".", "")
            elif dot_count == 1 and comma_count == 0:
                # Format: 1234.56
                normalized = value.replace(" ", "")
            else:
                # No decimal separator
                normalized = value.replace(" ", "")

            return float(normalized)
        except (ValueError, TypeError):
            return None

    def _find_all_amounts(self, text: str) -> list[float]:
        """Find all numeric amounts in text."""
        pattern = r"\b(\d{1,3}(?:[\s.]\d{3})*(?:[,\.]\d{2})|\d+(?:[,\.]\d{2}))\b"
        matches = re.findall(pattern, text)
        amounts: list[float] = []
        for match in matches:
            parsed = self._parse_amount(match)
            if parsed is not None and parsed > 0:
                amounts.append(parsed)
        return sorted(set(amounts), reverse=True)[:5]


invoice_field_parser = InvoiceFieldParser()
