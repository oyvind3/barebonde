"""OCR and text extraction service for bilag recognition."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import io
import re
from typing import Any, Optional

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from pypdf import PdfReader

from app.core.config import settings
from app.services.invoice_field_parser import FieldCandidate, invoice_field_parser


@dataclass
class OCRResult:
    text: str
    provider: str
    confidence: Optional[float]
    warnings: list[str]


@dataclass
class ExtractedFields:
    """Structured fields extracted from OCR text."""

    supplier_name: Optional[FieldCandidate] = None
    org_number: Optional[FieldCandidate] = None
    invoice_number: Optional[FieldCandidate] = None
    invoice_date: Optional[FieldCandidate] = None
    due_date: Optional[FieldCandidate] = None
    amount_total: Optional[FieldCandidate] = None
    amount_vat: Optional[FieldCandidate] = None
    amount_excl_vat: Optional[FieldCandidate] = None
    currency: Optional[FieldCandidate] = None
    kid: Optional[FieldCandidate] = None
    bank_account: Optional[FieldCandidate] = None
    description: Optional[FieldCandidate] = None
    text_preview: Optional[str] = None


class OCRService:
    def __init__(self) -> None:
        self.endpoint = settings.azure_document_intelligence_endpoint
        self.key = settings.azure_document_intelligence_key
        self.default_language = settings.ocr_default_language or "nb"

    def _can_use_azure_ocr(self) -> bool:
        return bool(self.endpoint and self.key)

    def _extract_with_azure(self, payload: bytes) -> OCRResult:
        client = DocumentAnalysisClient(self.endpoint, AzureKeyCredential(self.key))
        poller = client.begin_analyze_document("prebuilt-read", document=payload, locale=self.default_language)
        result = poller.result()

        lines: list[str] = []
        confidences: list[float] = []
        for page in result.pages or []:
            for line in page.lines or []:
                if line.content:
                    lines.append(line.content)
                if getattr(line, "spans", None) and page.words:
                    # Confidence is only available on words; aggregate word confidence when possible.
                    confidences.extend([float(word.confidence) for word in page.words if word.confidence is not None])

        avg_confidence = sum(confidences) / len(confidences) if confidences else None
        return OCRResult(
            text="\n".join(lines).strip(),
            provider="azure-document-intelligence",
            confidence=avg_confidence,
            warnings=[],
        )

    def _extract_pdf_text(self, payload: bytes) -> OCRResult:
        reader = PdfReader(io.BytesIO(payload))
        pages_text = []
        for page in reader.pages:
            pages_text.append((page.extract_text() or "").strip())

        text = "\n".join([page for page in pages_text if page]).strip()
        warning = []
        if not text:
            warning.append("PDF inneholdt lite eller ingen maskinlesbar tekst")

        return OCRResult(
            text=text,
            provider="pypdf-fallback",
            confidence=None,
            warnings=warning,
        )

    def _extract_plain_text(self, payload: bytes) -> OCRResult:
        warning: list[str] = []
        text = ""
        for encoding in ("utf-8", "latin-1"):
            try:
                text = payload.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if not text:
            warning.append("Klarte ikke dekode tekstinnhold")

        return OCRResult(
            text=text.strip(),
            provider="text-fallback",
            confidence=None,
            warnings=warning,
        )

    def extract_text(self, payload: bytes, content_type: str, file_name: str) -> OCRResult:
        content_type = (content_type or "").lower()
        extension = ""
        if "." in file_name:
            extension = file_name.rsplit(".", 1)[-1].lower()

        warnings: list[str] = []

        if self._can_use_azure_ocr() and (
            content_type.startswith("image/")
            or content_type == "application/pdf"
            or extension in {"jpg", "jpeg", "png", "webp", "pdf", "heic", "tiff", "bmp"}
        ):
            try:
                return self._extract_with_azure(payload)
            except Exception:
                # Provider details can contain request identifiers or service data;
                # keep the stored warning safe for later display.
                warnings.append("OCR-tjenesten var utilgjengelig; lokal fallback ble brukt")

        if content_type == "application/pdf" or extension == "pdf":
            fallback = self._extract_pdf_text(payload)
            fallback.warnings.extend(warnings)
            return fallback

        if content_type.startswith("text/") or extension in {"txt", "csv", "json", "xml"}:
            fallback = self._extract_plain_text(payload)
            fallback.warnings.extend(warnings)
            return fallback

        # Unknown binary file types may still contain sparse text bytes.
        fallback = self._extract_plain_text(payload)
        fallback.provider = "binary-fallback"
        fallback.warnings.append("Filtype ikke optimal for OCR; resultat kan være svakt")
        fallback.warnings.extend(warnings)
        return fallback

    def infer_fields(self, text: str) -> dict[str, Any]:
        """Legacy method for backward compatibility.

        Returns simple field suggestions from OCR text.
        """
        parsed = invoice_field_parser.parse_fields(text)

        amount_total = parsed.get("amount_total")
        date_candidate = parsed.get("invoice_date")
        supplier_candidate = parsed.get("supplier_name")

        return {
            "suggested_amount": float(amount_total.value) if amount_total else None,
            "suggested_date": date_candidate.value if date_candidate else None,
            "suggested_supplier": supplier_candidate.value if supplier_candidate else None,
            "text_preview": parsed.get("text_preview"),
            # New structured fields
            "extracted_fields": {
                "supplier_name": self._field_to_dict(supplier_candidate),
                "org_number": self._field_to_dict(parsed.get("org_number")),
                "invoice_number": self._field_to_dict(parsed.get("invoice_number")),
                "invoice_date": self._field_to_dict(date_candidate),
                "due_date": self._field_to_dict(parsed.get("due_date")),
                "amount_total": self._field_to_dict(amount_total),
                "amount_vat": self._field_to_dict(parsed.get("amount_vat")),
                "currency": self._field_to_dict(parsed.get("currency")),
                "kid": self._field_to_dict(parsed.get("kid")),
                "bank_account": self._field_to_dict(parsed.get("bank_account")),
            },
        }

    def extract_structured_fields(self, text: str) -> ExtractedFields:
        """Extract structured fields from OCR text with confidence scores."""
        parsed = invoice_field_parser.parse_fields(text)
        return ExtractedFields(
            supplier_name=parsed.get("supplier_name"),
            org_number=parsed.get("org_number"),
            invoice_number=parsed.get("invoice_number"),
            invoice_date=parsed.get("invoice_date"),
            due_date=parsed.get("due_date"),
            amount_total=parsed.get("amount_total"),
            amount_vat=parsed.get("amount_vat"),
            amount_excl_vat=parsed.get("amount_excl_vat"),
            currency=parsed.get("currency"),
            kid=parsed.get("kid"),
            bank_account=parsed.get("bank_account"),
            description=parsed.get("description"),
            text_preview=parsed.get("text_preview"),
        )

    def _field_to_dict(self, field: Optional[Any]) -> Optional[dict[str, Any]]:
        """Convert FieldCandidate to dictionary for JSON serialization."""
        if field is None:
            return None
        return {
            "value": field.value,
            "confidence": field.confidence,
            "source": field.source,
            "needs_review": field.needs_review,
            "label_context": field.label_context,
        }

    def _extract_amount_candidates(self, text: str) -> list[float]:
        """Legacy method - kept for backward compatibility."""
        return [float(c.value) for c in invoice_field_parser._find_all_amounts(text)][:3]

    def _extract_date_candidate(self, text: str) -> Optional[str]:
        """Legacy method - kept for backward compatibility."""
        result = invoice_field_parser._find_any_date(text)
        return result.value if result else None

    def _extract_supplier_candidate(self, lines: list[str]) -> Optional[str]:
        """Legacy method - kept for backward compatibility."""
        result = invoice_field_parser._extract_supplier_name(lines)
        return result.value if result else None


ocr_service = OCRService()
