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


@dataclass
class OCRResult:
    text: str
    provider: str
    confidence: Optional[float]
    warnings: list[str]


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
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        normalized = "\n".join(lines)

        amount_candidates = self._extract_amount_candidates(normalized)
        date_candidate = self._extract_date_candidate(normalized)
        supplier_candidate = self._extract_supplier_candidate(lines)

        return {
            "suggested_amount": amount_candidates[0] if amount_candidates else None,
            "suggested_date": date_candidate,
            "suggested_supplier": supplier_candidate,
            "text_preview": normalized[:1200],
        }

    def _extract_amount_candidates(self, text: str) -> list[float]:
        # Captures values like 1 234,56 / 1234.56 / NOK 2.500,00.
        pattern = r"(?:NOK|kr|KR)?\s*(\d{1,3}(?:[\s.]\d{3})*(?:[,\.]\d{2})|\d+(?:[,\.]\d{2}))"
        raw_matches = re.findall(pattern, text)
        candidates: list[float] = []

        for match in raw_matches:
            value = match.replace(" ", "")
            if value.count(",") == 1 and value.count(".") >= 1:
                value = value.replace(".", "").replace(",", ".")
            elif value.count(",") == 1:
                value = value.replace(",", ".")
            elif value.count(".") > 1:
                value = value.replace(".", "")

            try:
                parsed = float(value)
            except ValueError:
                continue

            if parsed > 0:
                candidates.append(parsed)

        candidates = sorted(set(candidates), reverse=True)
        return candidates[:3]

    def _extract_date_candidate(self, text: str) -> Optional[str]:
        patterns = [
            r"\b(\d{4})-(\d{2})-(\d{2})\b",
            r"\b(\d{2})\.(\d{2})\.(\d{4})\b",
            r"\b(\d{2})/(\d{2})/(\d{4})\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if not match:
                continue

            groups = match.groups()
            try:
                if pattern.startswith(r"\b(\d{4})"):
                    dt = datetime(int(groups[0]), int(groups[1]), int(groups[2]))
                else:
                    dt = datetime(int(groups[2]), int(groups[1]), int(groups[0]))
                return dt.date().isoformat()
            except ValueError:
                continue

        return None

    def _extract_supplier_candidate(self, lines: list[str]) -> Optional[str]:
        for line in lines[:8]:
            cleaned = re.sub(r"\s+", " ", line).strip()
            if len(cleaned) < 3:
                continue
            if re.search(r"org\.nr|faktura|dato|sum|mva", cleaned, flags=re.IGNORECASE):
                continue
            if any(ch.isalpha() for ch in cleaned):
                return cleaned[:80]
        return None


ocr_service = OCRService()
