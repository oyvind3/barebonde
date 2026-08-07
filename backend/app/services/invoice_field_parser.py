"""Deterministic invoice field extraction service.

This module extracts structured fields from OCR text without using generative AI.
It supports Norwegian formats and prioritizes label-context over random regex matches.

Scoring principles:
- Explicit label match (same line): high confidence
- Label on previous line, value on next: medium-high confidence
- Distance from label reduces confidence
- Valid format / checksum increases confidence
- Conflicts between fields reduce confidence and add warnings
- Mathematical consistency (excl + vat = total) is cross-checked
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
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
    warnings: list[str] = field(default_factory=list)


# --- Label pattern definitions ---
# Each entry: (compiled_regex, base_confidence, label_name)
# Patterns are matched case-insensitively against individual lines.

_ORG_LABEL_PATTERNS = [
    (re.compile(r"org\.?\s*nr\.?\s*[:\-]?\s*$", re.I), 0.92, "org.nr"),
    (re.compile(r"organisasjonsnum(?:mer|r)\.?\s*[:\-]?\s*$", re.I), 0.92, "organisasjonsnummer"),
    (re.compile(r"foretaksnum(?:mer|r)\.?\s*[:\-]?\s*$", re.I), 0.90, "foretaksnummer"),
]

_ORG_INLINE_PATTERNS = [
    # "Org.nr: 123 456 789" or "Org.nr 123456789"
    (re.compile(r"org\.?\s*nr\.?\s*[:\-]?\s*(\d[\d\s]{7,12}\d)", re.I), 0.92, "org.nr"),
    (re.compile(r"organisasjonsnum(?:mer|r)\.?\s*[:\-]?\s*(\d[\d\s]{7,12}\d)", re.I), 0.92, "organisasjonsnummer"),
    # "NO 123 456 789 MVA" or "NO123456789MVA"
    (re.compile(r"\bNO\s*(\d[\d\s]{7,12}\d)\s*MVA\b", re.I), 0.93, "NO...MVA"),
    # "123 456 789 MVA" without country prefix (common in invoice footers)
    (re.compile(r"\b(\d[\d\s]{7,12}\d)\s*MVA\b", re.I), 0.85, "...MVA"),
]

_SUPPLIER_LABELS = [
    (re.compile(r"leverandør(?!\w)\s*[:\-]?\s*$", re.I), 0.85, "leverandør"),
    (re.compile(r"selger(?!\w)\s*[:\-]?\s*$", re.I), 0.80, "selger"),
    (re.compile(r"avsender(?!\w)\s*[:\-]?\s*$", re.I), 0.78, "avsender"),
]

_SUPPLIER_INLINE = [
    (re.compile(r"leverandør(?!\w)\s*[:\-]?\s*(.{3,80})", re.I), 0.85, "leverandør"),
    (re.compile(r"selger(?!\w)\s*[:\-]?\s*(.{3,80})", re.I), 0.80, "selger"),
    (re.compile(r"avsender(?!\w)\s*[:\-]?\s*(.{3,80})", re.I), 0.78, "avsender"),
]

_INVOICE_NUMBER_LABELS = [
    (re.compile(r"faktura\s*nr\.?\s*[:\-]?\s*$", re.I), 0.90, "fakturanr"),
    (re.compile(r"fakturanummer\s*[:\-]?\s*$", re.I), 0.90, "fakturanummer"),
    (re.compile(r"invoice\s*no\.?\s*[:\-]?\s*$", re.I), 0.88, "invoice no"),
    (re.compile(r"faktura\s*id\s*[:\-]?\s*$", re.I), 0.80, "faktura id"),
]

_INVOICE_NUMBER_INLINE = [
    (re.compile(r"faktura\s*nr\.?\s*[:\-]?\s*([A-Za-z0-9\-/]+)", re.I), 0.90, "fakturanr"),
    (re.compile(r"fakturanummer\s*[:\-]?\s*([A-Za-z0-9\-/]+)", re.I), 0.90, "fakturanummer"),
    (re.compile(r"invoice\s*no\.?\s*[:\-]?\s*([A-Za-z0-9\-/]+)", re.I), 0.88, "invoice no"),
]

_INVOICE_DATE_LABELS = [
    (re.compile(r"faktura\s*dato\s*[:\-]?\s*$", re.I), 0.90, "fakturadato"),
    (re.compile(r"fakturadato\s*[:\-]?\s*$", re.I), 0.90, "fakturadato"),
    (re.compile(r"invoice\s*date\s*[:\-]?\s*$", re.I), 0.88, "invoice date"),
    (re.compile(r"utstedt\s*[:\-]?\s*$", re.I), 0.80, "utstedt"),
]

_INVOICE_DATE_INLINE = [
    (re.compile(r"faktura\s*dato\s*[:\-]?\s*(\d{2}[./\-]\d{2}[./\-]\d{2,4}|\d{4}-\d{2}-\d{2})", re.I), 0.90, "fakturadato"),
    (re.compile(r"fakturadato\s*[:\-]?\s*(\d{2}[./\-]\d{2}[./\-]\d{2,4}|\d{4}-\d{2}-\d{2})", re.I), 0.90, "fakturadato"),
    (re.compile(r"invoice\s*date\s*[:\-]?\s*(\d{2}[./\-]\d{2}[./\-]\d{2,4}|\d{4}-\d{2}-\d{2})", re.I), 0.88, "invoice date"),
]

_DUE_DATE_LABELS = [
    (re.compile(r"forfalls\s*dato\s*[:\-]?\s*$", re.I), 0.90, "forfallsdato"),
    (re.compile(r"forfallsdato\s*[:\-]?\s*$", re.I), 0.90, "forfallsdato"),
    (re.compile(r"forfall\s*[:\-]?\s*$", re.I), 0.88, "forfall"),
    (re.compile(r"betalingsfrist\s*[:\-]?\s*$", re.I), 0.88, "betalingsfrist"),
    (re.compile(r"due\s*date\s*[:\-]?\s*$", re.I), 0.85, "due date"),
]

_DUE_DATE_INLINE = [
    (re.compile(r"forfalls\s*dato\s*[:\-]?\s*(\d{2}[./\-]\d{2}[./\-]\d{2,4}|\d{4}-\d{2}-\d{2})", re.I), 0.90, "forfallsdato"),
    (re.compile(r"forfallsdato\s*[:\-]?\s*(\d{2}[./\-]\d{2}[./\-]\d{2,4}|\d{4}-\d{2}-\d{2})", re.I), 0.90, "forfallsdato"),
    (re.compile(r"forfall\s*[:\-]?\s*(\d{2}[./\-]\d{2}[./\-]\d{2,4}|\d{4}-\d{2}-\d{2})", re.I), 0.88, "forfall"),
    (re.compile(r"betalingsfrist\s*[:\-]?\s*(\d{2}[./\-]\d{2}[./\-]\d{2,4}|\d{4}-\d{2}-\d{2})", re.I), 0.88, "betalingsfrist"),
]

_TOTAL_LABELS = [
    (re.compile(r"(?:beløp\s+)?[åa]\s+betale\s*[:\-]?\s*$", re.I), 0.95, "å betale"),
    (re.compile(r"beløp\s+[åa]\s+betale\s*[:\-]?\s*$", re.I), 0.95, "beløp å betale"),
    (re.compile(r"sum\s+[åa]\s+betale\s*[:\-]?\s*$", re.I), 0.95, "sum å betale"),
    (re.compile(r"total(?:t)?\s*(?:inkl\.?\s*mva\.?)?\s*[:\-]?\s*$", re.I), 0.90, "total"),
    (re.compile(r"sum\s+inkl\.?\s*mva\.?\s*[:\-]?\s*$", re.I), 0.92, "sum inkl. mva"),
]

_TOTAL_INLINE = [
    (re.compile(r"(?:beløp\s+)?[åa]\s+betale\s*[:\-]?\s*(?:NOK|kr\.?)?\s*([\d][\d\s.,]*)", re.I), 0.95, "å betale"),
    (re.compile(r"total(?:t)?\s*(?:inkl\.?\s*mva\.?)?\s*[:\-]?\s*(?:NOK|kr\.?)?\s*([\d][\d\s.,]*)", re.I), 0.90, "total"),
    (re.compile(r"sum\s+inkl\.?\s*mva\.?\s*[:\-]?\s*(?:NOK|kr\.?)?\s*([\d][\d\s.,]*)", re.I), 0.92, "sum inkl. mva"),
]

_EXCL_VAT_LABELS = [
    (re.compile(r"(?:sum\s+)?eks\.?\s*mva\.?\s*[:\-]?\s*$", re.I), 0.90, "eks. mva"),
    (re.compile(r"netto\s*[:\-]?\s*$", re.I), 0.85, "netto"),
    (re.compile(r"subtotal\s*[:\-]?\s*$", re.I), 0.82, "subtotal"),
    (re.compile(r"sum\s+eks\.?\s*merverdiavgift\s*[:\-]?\s*$", re.I), 0.90, "eks. mva"),
]

_EXCL_VAT_INLINE = [
    (re.compile(r"(?:sum\s+)?eks\.?\s*mva\.?\s*[:\-]?\s*(?:NOK|kr\.?)?\s*([\d][\d\s.,]*)", re.I), 0.90, "eks. mva"),
    (re.compile(r"netto\s*[:\-]?\s*(?:NOK|kr\.?)?\s*([\d][\d\s.,]*)", re.I), 0.85, "netto"),
]

# Negative lookbehind: "MVA" preceded by "eks." / "inkl." (with or without a
# following space) is not a VAT amount. Each lookbehind must be fixed-length.
_VAT_NOT_EXCL = (
    r"(?<!eks\.\s)(?<!eks\.)(?<!eks\s)"
    r"(?<!inkl\.\s)(?<!inkl\.)(?<!inkl\s)"
)

_VAT_LABELS = [
    (re.compile(_VAT_NOT_EXCL + r"(?:herav\s+)?mva(?:\.?\s*beløp)?\s*[:\-]?\s*$", re.I), 0.90, "mva"),
    (re.compile(_VAT_NOT_EXCL + r"mva\s*\d+\s*%\s*[:\-]?\s*$", re.I), 0.88, "mva %"),
    (re.compile(_VAT_NOT_EXCL + r"merverdiavgift\s*[:\-]?\s*$", re.I), 0.88, "merverdiavgift"),
]

_VAT_INLINE = [
    (re.compile(_VAT_NOT_EXCL + r"(?:herav\s+)?mva(?:\.?\s*beløp)?\s*[:\-]?\s*(?:NOK|kr\.?)?\s*([\d][\d\s.,]*)", re.I), 0.90, "mva"),
    (re.compile(_VAT_NOT_EXCL + r"merverdiavgift\s*[:\-]?\s*(?:NOK|kr\.?)?\s*([\d][\d\s.,]*)", re.I), 0.88, "merverdiavgift"),
]

_KID_LABELS = [
    (re.compile(r"KID(?:\s*-?\s*nr\.?)?\s*[:\-]?\s*$", re.I), 0.92, "KID"),
    (re.compile(r"betalingsreferanse\s*[:\-]?\s*$", re.I), 0.85, "betalingsreferanse"),
    (re.compile(r"OCR\s*-?\s*KID\s*[:\-]?\s*$", re.I), 0.90, "OCR KID"),
]

_KID_INLINE = [
    (re.compile(r"KID(?:\s*-?\s*nr\.?)?\s*[:\-]?\s*([\d][\d\s]{3,26})", re.I), 0.92, "KID"),
    (re.compile(r"betalingsreferanse\s*[:\-]?\s*([\d][\d\s]{3,26})", re.I), 0.85, "betalingsreferanse"),
]

_BANK_LABELS = [
    (re.compile(r"bank\s*konto(?:\s*nr\.?)?\s*[:\-]?\s*$", re.I), 0.90, "bankkonto"),
    (re.compile(r"kontonummer\s*[:\-]?\s*$", re.I), 0.90, "kontonummer"),
    (re.compile(r"konto\s*nr\.?\s*[:\-]?\s*$", re.I), 0.85, "konto nr"),
    (re.compile(r"giro\s*konto\s*[:\-]?\s*$", re.I), 0.85, "girokonto"),
    (re.compile(r"^konto\s*[:\-]?\s*$", re.I), 0.80, "konto"),
]

_BANK_INLINE = [
    (re.compile(r"bank\s*konto(?:\s*nr\.?)?\s*[:\-]?\s*(\d{4}[.\s]?\d{2}[.\s]?\d{5})", re.I), 0.90, "bankkonto"),
    (re.compile(r"kontonummer\s*[:\-]?\s*(\d{4}[.\s]?\d{2}[.\s]?\d{5})", re.I), 0.90, "kontonummer"),
    (re.compile(r"\bkonto\s*[:\-]?\s*(\d{4}[.\s]?\d{2}[.\s]?\d{5})", re.I), 0.85, "konto"),
]

_DATE_RE = re.compile(r"\d{2}[./\-]\d{2}[./\-]\d{2,4}|\d{4}-\d{2}-\d{2}")
_AMOUNT_RE = re.compile(r"[\d][\d\s.,]*[\d]|[\d]")
_ORG_RE = re.compile(r"\d[\d\s]{7,12}\d")


class InvoiceFieldParser:
    """Extract invoice fields from OCR text using deterministic rules with candidate scoring."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_fields(self, text: str) -> dict[str, Any]:
        """Parse all invoice fields from OCR text.

        Returns a dictionary with suggested values and confidence scores.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        normalized = "\n".join(lines)
        warnings: list[str] = []

        supplier_name = self._extract_supplier_name(lines)
        org_number = self._extract_org_number(lines, normalized)
        invoice_number = self._extract_invoice_number(lines)
        invoice_date = self._extract_invoice_date(lines)
        due_date = self._extract_due_date(lines)
        amount_excl_vat = self._extract_amount_excl_vat(lines)
        amount_vat = self._extract_vat_amount(lines)
        amount_total = self._extract_total_amount(lines, amount_excl_vat, amount_vat)

        # Derived fallback: if no labeled total was found but both excl and vat
        # are present and consistent, suggest total = excl + vat.
        if amount_total is None and amount_excl_vat and amount_vat:
            try:
                derived = float(amount_excl_vat.value) + float(amount_vat.value)
                if derived > 0:
                    amount_total = FieldCandidate(
                        value=str(derived),
                        confidence=0.55,
                        source="inferred",
                        needs_review=True,
                        label_context="derived (eks. MVA + MVA)",
                    )
            except (ValueError, TypeError):
                pass

        currency = self._extract_currency(normalized)
        kid = self._extract_kid(lines)
        bank_account = self._extract_bank_account(lines)
        description = self._extract_description(lines)

        # --- Cross-checks ---
        self._resolve_identifier_conflicts(org_number, kid, bank_account, warnings)
        self._cross_check_amounts(amount_total, amount_excl_vat, amount_vat, warnings)
        self._cross_check_dates(invoice_date, due_date, warnings)

        return {
            "supplier_name": supplier_name,
            "org_number": org_number,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "due_date": due_date,
            "amount_total": amount_total,
            "amount_vat": amount_vat,
            "amount_excl_vat": amount_excl_vat,
            "currency": currency,
            "kid": kid,
            "bank_account": bank_account,
            "description": description,
            "text_preview": normalized[:1200],
            "warnings": warnings,
        }

    # ------------------------------------------------------------------
    # Line-based extraction helpers
    # ------------------------------------------------------------------

    def _find_labeled_value(
        self,
        lines: list[str],
        label_patterns: list[tuple[re.Pattern, float, str]],
        inline_patterns: list[tuple[re.Pattern, float, str]],
        value_regex: re.Pattern,
        max_distance: int = 2,
    ) -> Optional[FieldCandidate]:
        """Generic label-context extraction.

        1. Try inline patterns (label + value on same line).
        2. Try label-only patterns: if a line matches a label, look at the
           same line remainder and the next `max_distance` lines for a value.
        """
        candidates: list[FieldCandidate] = []

        # Pass 1: inline patterns
        for line in lines:
            for pattern, base_conf, label_name in inline_patterns:
                match = pattern.search(line)
                if match:
                    value = match.group(1).strip()
                    if value:
                        candidates.append(
                            FieldCandidate(
                                value=value,
                                confidence=base_conf,
                                source="ocr",
                                needs_review=base_conf < 0.85,
                                label_context=label_name,
                            )
                        )

        # Pass 2: label on its own line, value on same/next line(s)
        for idx, line in enumerate(lines):
            for pattern, base_conf, label_name in label_patterns:
                if pattern.search(line):
                    # Check remainder of same line after label
                    remainder = pattern.sub("", line).strip()
                    val_match = value_regex.search(remainder)
                    if val_match:
                        candidates.append(
                            FieldCandidate(
                                value=val_match.group(0).strip(),
                                confidence=base_conf,
                                source="ocr",
                                needs_review=base_conf < 0.85,
                                label_context=label_name,
                            )
                        )
                        continue
                    # Check next lines with distance penalty
                    for offset in range(1, max_distance + 1):
                        if idx + offset >= len(lines):
                            break
                        next_line = lines[idx + offset]
                        val_match = value_regex.search(next_line)
                        if val_match:
                            distance_penalty = 0.05 * offset
                            conf = max(0.3, base_conf - distance_penalty)
                            candidates.append(
                                FieldCandidate(
                                    value=val_match.group(0).strip(),
                                    confidence=conf,
                                    source="ocr",
                                    needs_review=conf < 0.80,
                                    label_context=label_name,
                                )
                            )
                            break

        if not candidates:
            return None
        return self._select_best_candidate(candidates)

    def _select_best_candidate(self, candidates: list[FieldCandidate]) -> FieldCandidate:
        """Pick the best candidate, rewarding uniqueness and penalizing conflicts."""
        # Deduplicate by normalized value, keeping highest confidence per value
        by_value: dict[str, FieldCandidate] = {}
        for cand in candidates:
            key = re.sub(r"\s+", "", cand.value).casefold()
            if key not in by_value or cand.confidence > by_value[key].confidence:
                by_value[key] = cand
        unique = sorted(by_value.values(), key=lambda c: -c.confidence)
        best = unique[0]

        if len(unique) == 1:
            # Unique candidate: small confidence bonus
            best.confidence = min(1.0, best.confidence + 0.02)
        else:
            distinct = {re.sub(r"\s+", "", u.value) for u in unique}
            if len(distinct) > 1:
                # Multiple distinct values found – reduce confidence, flag review
                best.confidence = max(0.3, best.confidence - 0.15)
                best.needs_review = True
                best.warnings.append("Flere mulige verdier funnet – kontroller")

        best.needs_review = best.needs_review or best.confidence < 0.80
        return best

    # ------------------------------------------------------------------
    # Field extractors
    # ------------------------------------------------------------------

    def _extract_supplier_name(self, lines: list[str]) -> Optional[FieldCandidate]:
        """Extract supplier name from the first few lines."""
        skip_re = re.compile(
            r"org\.nr|organisasjonsnummer|faktura|dato|sum|mva|total|kunde|kundeservice|"
            r"telefon|e-post|www\.|side|page|fakturanr|kontonummer|bankkonto|kid|forfall",
            re.IGNORECASE,
        )
        for line in lines[:12]:
            cleaned = re.sub(r"\s+", " ", line).strip()
            if len(cleaned) < 3:
                continue
            if skip_re.search(cleaned):
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

    def _extract_org_number(self, lines: list[str], text: str) -> Optional[FieldCandidate]:
        """Extract Norwegian organization number (9 digits)."""
        # Try labeled extraction first
        candidate = self._find_labeled_value(
            lines, _ORG_LABEL_PATTERNS, _ORG_INLINE_PATTERNS, _ORG_RE
        )
        if candidate:
            digits = re.sub(r"\s", "", candidate.value)
            # Handle "NO xxx xxx xxx MVA" – strip non-digits
            digits = re.sub(r"[^0-9]", "", digits)
            if len(digits) == 9 and self._validate_org_number(digits):
                candidate.value = digits
                return candidate
            # If labeled but invalid, reduce confidence
            candidate.confidence = max(0.3, candidate.confidence - 0.3)
            candidate.needs_review = True
            candidate.warnings.append("Ugyldig organisasjonsnummer")
            return candidate

        # Fallback: standalone 9-digit numbers
        standalone_pattern = r"\b(\d{9})\b"
        matches = re.findall(standalone_pattern, text)
        for match in matches:
            if self._validate_org_number(match):
                return FieldCandidate(
                    value=match,
                    confidence=0.5,
                    source="inferred",
                    needs_review=True,
                )
        return None

    def _validate_org_number(self, org_nr: str) -> bool:
        """Validate Norwegian organization number (MOD 11 checksum)."""
        if len(org_nr) != 9 or not org_nr.isdigit():
            return False
        if org_nr == "000000000" or org_nr == "123456789":
            return False
        # MOD 11 checksum with weights [3,2,7,6,5,4,3,2]
        weights = [3, 2, 7, 6, 5, 4, 3, 2]
        total = sum(int(org_nr[i]) * weights[i] for i in range(8))
        remainder = total % 11
        check = 0 if remainder == 0 else 11 - remainder
        if check == 10:
            return False  # Invalid per MOD 11
        return check == int(org_nr[8])

    def _extract_invoice_number(self, lines: list[str]) -> Optional[FieldCandidate]:
        """Extract invoice number."""
        value_re = re.compile(r"[A-Za-z0-9\-/]{2,30}")
        candidate = self._find_labeled_value(
            lines, _INVOICE_NUMBER_LABELS, _INVOICE_NUMBER_INLINE, value_re
        )
        if candidate:
            # Clean up trailing punctuation
            candidate.value = candidate.value.strip("./-")
            if len(candidate.value) < 2:
                return None
        return candidate

    def _extract_invoice_date(self, lines: list[str]) -> Optional[FieldCandidate]:
        """Extract invoice date."""
        candidate = self._find_labeled_value(
            lines, _INVOICE_DATE_LABELS, _INVOICE_DATE_INLINE, _DATE_RE
        )
        if candidate:
            parsed = self._parse_date(candidate.value)
            if parsed:
                candidate.value = parsed.strftime("%Y-%m-%d")
                return candidate
            candidate.confidence = max(0.3, candidate.confidence - 0.3)
            candidate.needs_review = True
            candidate.warnings.append("Kunne ikke tolke datoformat")
            return candidate

        # Fallback: find any date in the text
        return self._find_any_date("\n".join(lines))

    def _extract_due_date(self, lines: list[str]) -> Optional[FieldCandidate]:
        """Extract due date (forfallsdato)."""
        candidate = self._find_labeled_value(
            lines, _DUE_DATE_LABELS, _DUE_DATE_INLINE, _DATE_RE
        )
        if candidate:
            parsed = self._parse_date(candidate.value)
            if parsed:
                candidate.value = parsed.strftime("%Y-%m-%d")
                return candidate
            candidate.confidence = max(0.3, candidate.confidence - 0.3)
            candidate.needs_review = True
            candidate.warnings.append("Kunne ikke tolke datoformat")
        return candidate

    def _extract_total_amount(
        self,
        lines: list[str],
        amount_excl_vat: Optional[FieldCandidate] = None,
        amount_vat: Optional[FieldCandidate] = None,
    ) -> Optional[FieldCandidate]:
        """Extract total amount including VAT.

        Prioritizes amounts linked to explicit total/payment labels. When both
        excl-VAT and VAT amounts are known, candidates matching their sum get a
        confidence bonus (mathematical consistency).
        """
        candidates: list[tuple[float, float, str]] = []

        # Pass 1: inline label patterns
        for line in lines:
            for pattern, base_conf, label_name in _TOTAL_INLINE:
                match = pattern.search(line)
                if match:
                    parsed = self._parse_amount(match.group(1))
                    if parsed is not None and parsed > 0:
                        candidates.append((parsed, base_conf, label_name))

        # Pass 2: label on own line, amount on same/next line
        for idx, line in enumerate(lines):
            for pattern, base_conf, label_name in _TOTAL_LABELS:
                if pattern.search(line):
                    # Same line remainder
                    remainder = pattern.sub("", line).strip()
                    amt_match = _AMOUNT_RE.search(remainder)
                    if amt_match:
                        parsed = self._parse_amount(amt_match.group(0))
                        if parsed is not None and parsed > 0:
                            candidates.append((parsed, base_conf, label_name))
                            continue
                    # Next lines
                    for offset in range(1, 3):
                        if idx + offset >= len(lines):
                            break
                        next_line = lines[idx + offset]
                        amt_match = _AMOUNT_RE.search(next_line)
                        if amt_match:
                            parsed = self._parse_amount(amt_match.group(0))
                            if parsed is not None and parsed > 0:
                                penalty = 0.05 * offset
                                candidates.append((parsed, max(0.4, base_conf - penalty), label_name))
                                break

        if not candidates:
            # Last resort: find all amounts, but mask out bank account numbers
            # and dates so "1234.56.78901" or "12.05.2026" are not misread.
            text = self._mask_bank_accounts("\n".join(lines))
            text = self._mask_dates(text)
            all_amounts = self._find_all_amounts(text)
            for amount in all_amounts[:3]:
                candidates.append((amount, 0.2, ""))

        if not candidates:
            return None

        # Math consistency bonus: if excl + vat is known, reward matching totals
        expected_sum: Optional[float] = None
        if amount_excl_vat and amount_vat:
            try:
                expected_sum = float(amount_excl_vat.value) + float(amount_vat.value)
            except (ValueError, TypeError):
                expected_sum = None

        def sort_key(item: tuple[float, float, str]) -> tuple[float, float]:
            amount, conf, _label = item
            bonus = 0.0
            if expected_sum is not None and abs(amount - expected_sum) <= max(0.5, expected_sum * 0.01):
                bonus = 0.10
            return (-(conf + bonus), -amount)

        candidates.sort(key=sort_key)
        best = candidates[0]
        final_conf = best[1]
        if expected_sum is not None and abs(best[0] - expected_sum) <= max(0.5, expected_sum * 0.01):
            final_conf = min(1.0, final_conf + 0.10)
        return FieldCandidate(
            value=str(best[0]),
            confidence=final_conf,
            source="ocr" if final_conf > 0.5 else "inferred",
            needs_review=final_conf < 0.7,
            label_context=best[2] if best[2] else None,
        )

    def _extract_amount_excl_vat(self, lines: list[str]) -> Optional[FieldCandidate]:
        """Extract amount excluding VAT."""
        candidate = self._find_labeled_value(
            lines, _EXCL_VAT_LABELS, _EXCL_VAT_INLINE, _AMOUNT_RE
        )
        if candidate:
            parsed = self._parse_amount(candidate.value)
            if parsed is not None and parsed > 0:
                candidate.value = str(parsed)
                return candidate
        return None

    def _extract_vat_amount(self, lines: list[str]) -> Optional[FieldCandidate]:
        """Extract VAT amount."""
        candidate = self._find_labeled_value(
            lines, _VAT_LABELS, _VAT_INLINE, _AMOUNT_RE
        )
        if candidate:
            parsed = self._parse_amount(candidate.value)
            if parsed is not None and parsed > 0:
                candidate.value = str(parsed)
                return candidate
        return None

    def _extract_currency(self, text: str) -> Optional[FieldCandidate]:
        """Extract currency code."""
        currency_patterns = [
            (re.compile(r"\b(NOK|nok)\b"), "NOK", 0.9),
            (re.compile(r"\b(EUR|Euro|EURO)\b", re.I), "EUR", 0.8),
            (re.compile(r"\b(USD|Dollar)\b", re.I), "USD", 0.8),
            (re.compile(r"\b(SEK)\b"), "SEK", 0.8),
            (re.compile(r"\b(DKK)\b"), "DKK", 0.8),
            (re.compile(r"\bkr\b", re.I), "NOK", 0.7),
        ]
        for pattern, currency, conf in currency_patterns:
            if pattern.search(text):
                return FieldCandidate(
                    value=currency,
                    confidence=conf,
                    source="ocr",
                    needs_review=conf < 0.85,
                )
        # Default to NOK
        return FieldCandidate(
            value="NOK",
            confidence=0.5,
            source="fallback",
            needs_review=False,
        )

    def _extract_kid(self, lines: list[str]) -> Optional[FieldCandidate]:
        """Extract KID (payment reference) number."""
        candidate = self._find_labeled_value(
            lines, _KID_LABELS, _KID_INLINE, re.compile(r"[\d][\d\s]{3,26}")
        )
        if candidate:
            kid = re.sub(r"\s", "", candidate.value)
            if 5 <= len(kid) <= 25 and kid.isdigit():
                candidate.value = kid
                # Validate MOD 10 or MOD 11 checksum if length is appropriate
                if self._validate_kid_mod10(kid) or self._validate_kid_mod11(kid):
                    candidate.confidence = min(1.0, candidate.confidence + 0.05)
                    candidate.needs_review = False
                else:
                    # Checksum invalid – reduce confidence but keep as suggestion
                    candidate.confidence = max(0.4, candidate.confidence - 0.2)
                    candidate.needs_review = True
                    candidate.warnings.append("KID-kontrollsiffer stemmer ikke")
                return candidate
            # Invalid format
            candidate.confidence = max(0.3, candidate.confidence - 0.3)
            candidate.needs_review = True
        return candidate

    def _validate_kid_mod10(self, kid: str) -> bool:
        """Validate KID using MOD 10 (Luhn) checksum."""
        if len(kid) < 2:
            return False
        try:
            digits = [int(d) for d in kid]
            # Luhn: double every second digit from right
            total = 0
            for i, d in enumerate(reversed(digits[:-1])):
                if i % 2 == 0:
                    d *= 2
                    if d > 9:
                        d -= 9
                total += d
            check = (10 - (total % 10)) % 10
            return check == digits[-1]
        except (ValueError, IndexError):
            return False

    def _validate_kid_mod11(self, kid: str) -> bool:
        """Validate KID using MOD 11 checksum."""
        if len(kid) < 2:
            return False
        try:
            digits = [int(d) for d in kid]
            weights = [2, 3, 4, 5, 6, 7]
            total = 0
            for i, d in enumerate(reversed(digits[:-1])):
                total += d * weights[i % len(weights)]
            remainder = total % 11
            check = 0 if remainder == 0 else 11 - remainder
            if check == 10:
                return False
            return check == digits[-1]
        except (ValueError, IndexError):
            return False

    def _extract_bank_account(self, lines: list[str]) -> Optional[FieldCandidate]:
        """Extract bank account number (Norwegian format: XXXX.XX.XXXXX)."""
        bank_re = re.compile(r"\d{4}[.\s]?\d{2}[.\s]?\d{5}")
        candidate = self._find_labeled_value(
            lines, _BANK_LABELS, _BANK_INLINE, bank_re
        )
        if candidate:
            # Normalize: remove spaces and dots for storage, but keep original format for display
            digits = re.sub(r"[.\s]", "", candidate.value)
            if len(digits) == 11 and digits.isdigit():
                # Store in standard format XXXX.XX.XXXXX
                candidate.value = f"{digits[:4]}.{digits[4:6]}.{digits[6:]}"
                return candidate
            candidate.confidence = max(0.3, candidate.confidence - 0.3)
            candidate.needs_review = True
        return candidate

    def _extract_description(self, lines: list[str]) -> Optional[FieldCandidate]:
        """Extract a short description from the document."""
        supplier = self._extract_supplier_name(lines)
        if supplier:
            return FieldCandidate(
                value=supplier.value,
                confidence=supplier.confidence * 0.8,
                source=supplier.source,
                needs_review=True,
            )
        return None

    # ------------------------------------------------------------------
    # Cross-checks
    # ------------------------------------------------------------------

    def _cross_check_amounts(
        self,
        total: Optional[FieldCandidate],
        excl: Optional[FieldCandidate],
        vat: Optional[FieldCandidate],
        warnings: list[str],
    ) -> None:
        """Cross-check amount consistency: excl + vat ≈ total."""
        if not total or not excl or not vat:
            return
        try:
            total_val = float(total.value)
            excl_val = float(excl.value)
            vat_val = float(vat.value)
        except (ValueError, TypeError):
            return

        computed = excl_val + vat_val
        tolerance = max(0.5, total_val * 0.01)  # 1% or 0.50 tolerance

        if abs(computed - total_val) > tolerance:
            warnings.append(
                f"Beløp stemmer ikke: eks. MVA ({excl_val:.2f}) + MVA ({vat_val:.2f}) "
                f"= {computed:.2f}, men total er {total_val:.2f}"
            )
            # Reduce confidence on all three
            total.confidence = max(0.3, total.confidence - 0.2)
            total.needs_review = True
            excl.confidence = max(0.3, excl.confidence - 0.2)
            excl.needs_review = True
            vat.confidence = max(0.3, vat.confidence - 0.2)
            vat.needs_review = True

    def _resolve_identifier_conflicts(
        self,
        org_number: Optional[FieldCandidate],
        kid: Optional[FieldCandidate],
        bank_account: Optional[FieldCandidate],
        warnings: list[str],
    ) -> None:
        """Detect when the same digit sequence is claimed by multiple identifier fields.

        If org number, KID, and bank account overlap, reduce confidence on the
        lower-confidence field and add a warning so the user can verify.
        """
        fields: list[tuple[str, Optional[FieldCandidate]]] = [
            ("organisasjonsnummer", org_number),
            ("KID", kid),
            ("bankkonto", bank_account),
        ]
        present = [(name, cand) for name, cand in fields if cand is not None]
        if len(present) < 2:
            return

        for i in range(len(present)):
            for j in range(i + 1, len(present)):
                name_a, cand_a = present[i]
                name_b, cand_b = present[j]
                digits_a = re.sub(r"\D", "", cand_a.value)
                digits_b = re.sub(r"\D", "", cand_b.value)
                if not digits_a or not digits_b:
                    continue
                if digits_a == digits_b or digits_a in digits_b or digits_b in digits_a:
                    warnings.append(
                        f"Samme tallsekvens brukt som både {name_a} og {name_b} – kontroller"
                    )
                    # Penalize the lower-confidence candidate
                    lower = cand_b if cand_a.confidence >= cand_b.confidence else cand_a
                    lower.confidence = max(0.3, lower.confidence - 0.2)
                    lower.needs_review = True

    def _cross_check_dates(
        self,
        invoice_date: Optional[FieldCandidate],
        due_date: Optional[FieldCandidate],
        warnings: list[str],
    ) -> None:
        """Cross-check: invoice_date <= due_date."""
        if not invoice_date or not due_date:
            return
        try:
            inv = datetime.strptime(invoice_date.value, "%Y-%m-%d")
            due = datetime.strptime(due_date.value, "%Y-%m-%d")
        except (ValueError, TypeError):
            return

        if inv > due:
            warnings.append(
                f"Fakturadato ({invoice_date.value}) er etter forfallsdato ({due_date.value})"
            )
            invoice_date.confidence = max(0.3, invoice_date.confidence - 0.2)
            invoice_date.needs_review = True
            due_date.confidence = max(0.3, due_date.confidence - 0.2)
            due_date.needs_review = True

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

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
                        value=parsed.strftime("%Y-%m-%d"),
                        confidence=0.5,
                        source="inferred",
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

        try:
            if comma_count == 1 and dot_count >= 1:
                # Format: 1.234,56 - remove dots, replace comma with dot
                normalized = value.replace(".", "").replace(",", ".")
            elif comma_count == 1 and dot_count == 0:
                # Format: 1234,56 or 1 234,56
                normalized = value.replace(" ", "").replace(",", ".")
            elif dot_count > 1:
                # Format: 1.234.567 or 1.234,56 with multiple dots
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

    def _mask_bank_accounts(self, text: str) -> str:
        """Mask Norwegian bank account numbers so they are not parsed as amounts.

        A bank account like "1234.56.78901" would otherwise match amount regexes
        and be misread as 1234.56. We replace them with a placeholder.
        """
        bank_re = re.compile(r"\d{4}[.\s]?\d{2}[.\s]?\d{5}")
        return bank_re.sub("BANKKONTO", text)

    def _mask_dates(self, text: str) -> str:
        """Mask date strings so they are not parsed as amounts.

        Dates like "12.05.2026" or "12/05/2026" would otherwise match amount
        regexes. We replace them with a placeholder before amount scanning.
        """
        date_re = re.compile(r"\d{2}[./\-]\d{2}[./\-]\d{2,4}|\d{4}-\d{2}-\d{2}")
        return date_re.sub("DATO", text)

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