"""Tenant-scoped voucher, document, journal, and reporting routes.

Epic 4: the double-entry journal is the accounting source of truth. The legacy
``accounting_transaction`` container is kept for compatibility but is no longer
a write path for new bookings.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
import logging
from typing import Any, Optional
from urllib.parse import quote
from uuid import uuid4

from azure.cosmos import exceptions
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.dependencies.entitlements import AuthorizedEntitlement, require_entitlement
from app.api.dependencies.farm_access import AuthorizedFarm, require_farm_permission
from app.core.permissions import Permission
from app.db.cosmos_client import (
    get_audit_logs_container,
    get_documents_container,
    get_farms_container,
    get_transactions_container,
)
from app.services import accounting_posting_service, journal_service
from app.services.accounting_catalog import (
    GLOSSARY,
    get_account,
    is_cash_account,
    search_accounts,
)
from app.services.journal_service import (
    DuplicateSourceError,
    JournalValidationError,
    PeriodLockedError,
    ore_to_kroner,
)
from app.services.ocr_service import OCRResult, ocr_service
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
    "image/tiff",
    "image/bmp",
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/json",
    "application/xml",
}
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
    "heic",
    "heif",
    "tiff",
    "bmp",
    "pdf",
    "txt",
    "csv",
    "json",
    "xml",
}


class DocumentResponse(BaseModel):
    id: str
    farm_id: str
    file_name: str
    content_type: str
    size_bytes: int = 0
    status: str
    created_at: Optional[str] = None
    created_by_user_id: Optional[str] = None
    # Do not expose raw OCR text, confidence or provider by default


class FieldSuggestion(BaseModel):
    value: Optional[Any] = None
    confidence: Optional[float] = None
    source: Optional[str] = None
    warnings: list[str] = []


class VoucherResponse(DocumentResponse):
    # User-confirmed fields (authoritative for booking)
    amount: float
    account_code: Optional[str]
    mva_code: Optional[str]
    voucher_date: str
    description: Optional[str]
    # Supplier fields
    supplier_name: Optional[str] = None
    supplier_org_number: Optional[str] = None
    # Invoice fields
    invoice_number: Optional[str] = None
    due_date: Optional[str] = None
    # Amount breakdown
    amount_excluding_vat: Optional[float] = None
    vat_amount: Optional[float] = None
    currency: str = "NOK"
    # Payment info
    kid: Optional[str] = None
    bank_account: Optional[str] = None
    # Document type
    document_type: str = "invoice"
    # OCR field suggestions with confidence for "Kontroller" markers
    field_suggestions: dict[str, Optional[FieldSuggestion]] = {}
    ocr_warnings: list[str] = []
    extraction_status: Optional[str] = None
    # Legacy OCR suggestions (kept for backward compatibility)
    ocr_suggested_amount: Optional[float] = None
    ocr_suggested_date: Optional[str] = None
    ocr_suggested_supplier: Optional[str] = None
    # Journal accounting references (Epic 4)
    journal_entry_id: Optional[str] = None
    journal_number: Optional[str] = None
    accounting_revision: int = 1


class TransactionResponse(BaseModel):
    id: str
    farm_id: str
    voucher_id: str
    transaction_type: str
    category: str
    amount: float
    account_code: str
    mva_code: Optional[str] = None
    description: str = ""
    voucher_date: str
    created_at: Optional[str] = None
    created_by_user_id: Optional[str] = None


class BookVoucherRequest(BaseModel):
    amount: float
    account_code: str
    mva_code: Optional[str] = None
    transaction_type: str = "expense"
    category: Optional[str] = None
    description: Optional[str] = None
    counter_account_code: Optional[str] = None
    voucher_date: Optional[str] = None


class CorrectBookingRequest(BaseModel):
    account_code: str
    counter_account_code: Optional[str] = None
    mva_code: Optional[str] = None
    transaction_type: str = "expense"
    amount: float
    amount_excluding_vat: Optional[float] = None
    vat_amount: Optional[float] = None
    description: Optional[str] = None
    correction_date: Optional[str] = None
    reason: str


class ReviewVoucherRequest(BaseModel):
    """Request to update user-confirmed fields on an unbooked voucher."""
    amount: Optional[float] = None
    voucher_date: Optional[str] = None
    description: Optional[str] = None
    # Supplier fields
    supplier_name: Optional[str] = None
    supplier_org_number: Optional[str] = None
    # Invoice fields
    invoice_number: Optional[str] = None
    due_date: Optional[str] = None
    # Amount breakdown
    amount_excluding_vat: Optional[float] = None
    vat_amount: Optional[float] = None
    currency: Optional[str] = None
    # Payment info
    kid: Optional[str] = None
    bank_account: Optional[str] = None
    # Document type
    document_type: Optional[str] = None
    # Accounting fields (set when ready for booking)
    account_code: Optional[str] = None
    mva_code: Optional[str] = None
    # Mark as reviewed and ready for booking
    ready_for_booking: bool = False


def _resource_not_found() -> HTTPException:
    # Do not reveal whether an ID belongs to another tenant.
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ressursen ble ikke funnet.")


def _tenant_mismatch() -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Farm-ID i requesten stemmer ikke med URL-en.")


def _service_unavailable(message: str, exc: Exception) -> HTTPException:
    logger.error("%s: %s", message, exc)
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=message)


def _is_not_found(exc: Exception) -> bool:
    return isinstance(exc, (exceptions.CosmosResourceNotFoundError, KeyError))


def _validate_file(content_type: str, size_bytes: int, file_name: str) -> None:
    extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    normalized_content_type = (content_type or "").split(";", 1)[0].strip().lower()

    if not file_name.strip() or size_bytes == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filen kan ikke være tom.")
    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Filen er for stor. Maks størrelse er 15 MB.",
        )
    if normalized_content_type == "application/octet-stream":
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Ukjent eller ugyldig filtype.")
        return
    if normalized_content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Filtypen støttes ikke.")
    if extension and extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Filendelsen støttes ikke.")


def _document_response(item: dict[str, Any]) -> DocumentResponse:
    return DocumentResponse(
        id=str(item["id"]),
        farm_id=str(item["farm_id"]),
        file_name=str(item.get("file_name") or "Bilag"),
        content_type=str(item.get("content_type") or "application/octet-stream"),
        size_bytes=int(item.get("size_bytes") or 0),
        status=str(item.get("status") or "mottatt"),
        created_at=item.get("created_at"),
        created_by_user_id=item.get("created_by_user_id"),
    )


def _voucher_response(item: dict[str, Any]) -> VoucherResponse:
    raw_suggestions = item.get("field_suggestions") or {}
    field_suggestions: dict[str, Optional[FieldSuggestion]] = {}
    for key, value in raw_suggestions.items():
        if isinstance(value, dict):
            field_suggestions[key] = FieldSuggestion(
                value=value.get("value"),
                confidence=value.get("confidence"),
                source=value.get("source"),
                warnings=value.get("warnings") or [],
            )
        else:
            field_suggestions[key] = None

    return VoucherResponse(
        **_document_response(item).model_dump(),
        amount=float(item.get("amount") or 0),
        account_code=item.get("account_code"),
        mva_code=item.get("mva_code"),
        voucher_date=str(item.get("voucher_date") or datetime.now(timezone.utc).date().isoformat()),
        description=item.get("description"),
        # Supplier fields
        supplier_name=item.get("supplier_name"),
        supplier_org_number=item.get("supplier_org_number"),
        # Invoice fields
        invoice_number=item.get("invoice_number"),
        due_date=item.get("due_date"),
        # Amount breakdown
        amount_excluding_vat=item.get("amount_excluding_vat"),
        vat_amount=item.get("vat_amount"),
        currency=item.get("currency", "NOK"),
        # Payment info
        kid=item.get("kid"),
        bank_account=item.get("bank_account"),
        # Document type
        document_type=item.get("document_type", "invoice"),
        # OCR field suggestions
        field_suggestions=field_suggestions,
        ocr_warnings=item.get("ocr_warnings") or [],
        extraction_status=item.get("extraction_status"),
        # Legacy OCR suggestions (kept for backward compatibility)
        ocr_suggested_amount=item.get("ocr_suggested_amount"),
        ocr_suggested_date=item.get("ocr_suggested_date"),
        ocr_suggested_supplier=item.get("ocr_suggested_supplier"),
        # Journal references
        journal_entry_id=item.get("journal_entry_id"),
        journal_number=str(item.get("journal_number")) if item.get("journal_number") is not None else None,
        accounting_revision=int(item.get("accounting_revision") or 1),
    )


def _transaction_response(item: dict[str, Any]) -> TransactionResponse:
    return TransactionResponse(
        id=str(item["id"]),
        farm_id=str(item["farm_id"]),
        voucher_id=str(item.get("voucher_id") or ""),
        transaction_type=str(item.get("transaction_type") or "expense"),
        category=str(item.get("category") or "Drift"),
        amount=float(item.get("amount") or 0),
        account_code=str(item.get("account_code") or ""),
        mva_code=item.get("mva_code"),
        description=str(item.get("description") or ""),
        voucher_date=str(item.get("voucher_date") or ""),
        created_at=item.get("created_at"),
        created_by_user_id=item.get("created_by_user_id"),
    )


def _read_document(*, farm_id: str, document_id: str) -> dict[str, Any]:
    try:
        item = get_documents_container().read_item(item=document_id, partition_key=farm_id)
    except Exception as exc:
        if _is_not_found(exc):
            raise _resource_not_found() from exc
        raise _service_unavailable("Dokumenttjenesten er utilgjengelig. Prøv igjen.", exc) from exc
    if item.get("farm_id") != farm_id:
        # Point reads should already enforce this; retain the check for malformed legacy documents.
        logger.warning("Document partition mismatch for document id %s", document_id)
        raise _resource_not_found()
    return item


def _read_voucher(*, farm_id: str, voucher_id: str) -> dict[str, Any]:
    item = _read_document(farm_id=farm_id, document_id=voucher_id)
    if item.get("type") != "voucher_document":
        raise _resource_not_found()
    return item


def _list_voucher_items(farm_id: str) -> list[dict[str, Any]]:
    query = "SELECT * FROM c WHERE c.farm_id = @farm_id AND c.type = 'voucher_document' ORDER BY c.created_at DESC"
    try:
        return list(
            get_documents_container().query_items(
                query=query,
                parameters=[{"name": "@farm_id", "value": farm_id}],
                partition_key=farm_id,
            )
        )
    except Exception as exc:
        raise _service_unavailable("Dokumenttjenesten er utilgjengelig. Prøv igjen.", exc) from exc


def _fetch_legacy_transactions(farm_id: str) -> list[dict[str, Any]]:
    """DEPRECATED: legacy transaction container, kept for compatibility only."""
    query = "SELECT * FROM c WHERE c.farm_id = @farm_id AND c.type = 'accounting_transaction'"
    try:
        return list(
            get_transactions_container().query_items(
                query=query,
                parameters=[{"name": "@farm_id", "value": farm_id}],
                partition_key=farm_id,
            )
        )
    except Exception as exc:
        raise _service_unavailable("Regnskapstjenesten er utilgjengelig. Prøv igjen.", exc) from exc


def _farm_is_vat_registered(farm_id: str) -> bool:
    try:
        farm = get_farms_container().read_item(item=farm_id, partition_key=farm_id)
    except Exception:
        return True
    vat = farm.get("vat_registered")
    if vat is None:
        return True
    if isinstance(vat, bool):
        return vat
    return str(vat).strip().lower() not in {"false", "no", "nei", "0"}


def _write_audit_event(event_type: str, farm_id: str, user_id: str) -> None:
    try:
        get_audit_logs_container().create_item(
            {
                "id": str(uuid4()),
                "type": "audit_log",
                "event_type": event_type,
                "farm_id": farm_id,
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as exc:
        # An audit failure must not make a completed financial operation look failed.
        logger.warning("Audit write failed for %s: %s", event_type, exc)


def _voucher_matches_filters(
    item: dict[str, Any],
    *,
    q: str = "",
    voucher_status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> bool:
    normalized_status = (voucher_status or "").strip().casefold()
    item_status = str(item.get("status") or "mottatt").casefold()
    if normalized_status and item_status != normalized_status:
        return False

    voucher_date = str(item.get("voucher_date") or "")
    if date_from and voucher_date < date_from.isoformat():
        return False
    if date_to and voucher_date > date_to.isoformat():
        return False

    normalized_query = q.strip().casefold()
    if not normalized_query:
        return True
    searchable_fields = (
        item.get("file_name"),
        item.get("description"),
        item.get("account_code"),
        item.get("ocr_suggested_supplier"),
        item.get("ocr_text_preview"),
    )
    return normalized_query in " ".join(str(value) for value in searchable_fields if value).casefold()


def _month_key(date_value: str) -> str:
    try:
        dt = datetime.fromisoformat(date_value)
    except ValueError:
        dt = datetime.now(timezone.utc)
    return f"{dt.year}-{dt.month:02d}"


def _journal_error_response(exc: Exception) -> HTTPException:
    if isinstance(exc, PeriodLockedError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, DuplicateSourceError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, (JournalValidationError, accounting_posting_service.PostingError)):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    logger.error("Journal posting failed: %s", exc)
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Bokføringen feilet. Prøv igjen.")


@router.get("/api/accounting/accounts")
async def get_accounts(
    query: str = Query(default=""),
    simple_mode: bool = Query(default=False),
) -> dict[str, Any]:
    """Return the static accounting catalog; it contains no tenant data."""
    return {"accounts": search_accounts(query=query, simple_mode=simple_mode), "glossary": GLOSSARY}


@router.post("/api/farms/{farm_id}/vouchers", response_model=VoucherResponse, status_code=status.HTTP_201_CREATED)
async def upload_voucher(
    farm_id: str,
    file: UploadFile = File(...),
    description: Optional[str] = Form(default=None),
    voucher_date: Optional[str] = Form(default=None),
    simple_mode: bool = Form(default=False),
    submitted_farm_id: Optional[str] = Form(default=None, alias="farm_id"),
    authorized: AuthorizedFarm = Depends(
        require_farm_permission(Permission.VOUCHER_CREATE, require_csrf_protection=True, require_active_farm=True)
    ),
) -> VoucherResponse:
    """Upload a voucher into the authorized Farm and persist safe metadata.
    
    OCR extraction runs asynchronously when available. User-confirmed fields
    are stored separately from raw OCR suggestions. The voucher status is set
    to 'needs_review' if OCR confidence is low or extraction failed.
    """
    if submitted_farm_id and submitted_farm_id != farm_id:
        raise _tenant_mismatch()

    payload = await file.read()
    content_type = (file.content_type or "application/octet-stream").split(";", 1)[0].lower()
    file_name = file.filename or "bilag"
    _validate_file(content_type, len(payload), file_name)

    document_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Extract text and structured fields
    try:
        ocr_result = ocr_service.extract_text(payload=payload, content_type=content_type, file_name=file_name)
        extracted = ocr_service.extract_structured_fields(ocr_result.text)
    except Exception as exc:
        logger.warning("OCR preprocessing failed for new voucher: %s", exc)
        ocr_result = OCRResult(text="", provider="unavailable", confidence=None, warnings=["OCR var ikke tilgjengelig"])
        extracted = None
    
    # Determine initial status based on extraction success
    extraction_status = "completed" if extracted else "failed"
    initial_status = "needs_review" if not extracted or ocr_result.warnings else "mottatt"

    try:
        blob = storage_service.upload_file(
            farm_id=farm_id,
            document_id=document_id,
            file_name=file_name,
            content_type=content_type,
            payload=payload,
        )
    except Exception as exc:
        raise _service_unavailable("Filopplasting er utilgjengelig. Prøv igjen.", exc) from exc

    # Build document with both user-confirmed and suggested fields
    document_item = {
        "id": document_id,
        "type": "voucher_document",
        "farm_id": farm_id,
        "file_name": file_name,
        "content_type": content_type,
        "size_bytes": blob["size_bytes"],
        "blob_name": blob["blob_name"],
        # User-confirmed fields (can be updated via PATCH before booking)
        "description": description,
        "voucher_date": voucher_date,
        "status": initial_status,
        "account_code": None,
        "mva_code": None,
        "amount": 0.0,
        # Supplier fields from OCR suggestions
        "supplier_name": extracted.supplier_name.value if extracted and extracted.supplier_name else None,
        "supplier_org_number": extracted.org_number.value if extracted and extracted.org_number else None,
        # Invoice fields from OCR suggestions
        "invoice_number": extracted.invoice_number.value if extracted and extracted.invoice_number else None,
        "due_date": extracted.due_date.value if extracted and extracted.due_date else None,
        # Amount fields from OCR suggestions
        "amount_excluding_vat": float(extracted.amount_excl_vat.value) if extracted and extracted.amount_excl_vat else None,
        "vat_amount": float(extracted.amount_vat.value) if extracted and extracted.amount_vat else None,
        "currency": extracted.currency.value if extracted and extracted.currency else "NOK",
        # Payment info from OCR suggestions
        "kid": extracted.kid.value if extracted and extracted.kid else None,
        "bank_account": extracted.bank_account.value if extracted and extracted.bank_account else None,
        # Document type detection (default to invoice)
        "document_type": "invoice",
        # Extraction metadata (not exposed in default API responses)
        "extraction_provider": ocr_result.provider,
        "extraction_status": extraction_status,
        "extracted_at": now if extracted else None,
        "field_suggestions": {
            "supplier_name": ocr_service._field_to_dict(extracted.supplier_name) if extracted and extracted.supplier_name else None,
            "org_number": ocr_service._field_to_dict(extracted.org_number) if extracted and extracted.org_number else None,
            "invoice_number": ocr_service._field_to_dict(extracted.invoice_number) if extracted and extracted.invoice_number else None,
            "invoice_date": ocr_service._field_to_dict(extracted.invoice_date) if extracted and extracted.invoice_date else None,
            "due_date": ocr_service._field_to_dict(extracted.due_date) if extracted and extracted.due_date else None,
            "amount_total": ocr_service._field_to_dict(extracted.amount_total) if extracted and extracted.amount_total else None,
            "amount_vat": ocr_service._field_to_dict(extracted.amount_vat) if extracted and extracted.amount_vat else None,
            "amount_excl_vat": ocr_service._field_to_dict(extracted.amount_excl_vat) if extracted and extracted.amount_excl_vat else None,
            "currency": ocr_service._field_to_dict(extracted.currency) if extracted and extracted.currency else None,
            "kid": ocr_service._field_to_dict(extracted.kid) if extracted and extracted.kid else None,
            "bank_account": ocr_service._field_to_dict(extracted.bank_account) if extracted and extracted.bank_account else None,
        } if extracted else {},
        # Legacy fields for backward compatibility
        "simple_mode": bool(simple_mode),
        "ocr_provider": ocr_result.provider,
        "ocr_confidence": ocr_result.confidence,
        "ocr_text_preview": extracted.text_preview if extracted else None,
        "ocr_warnings": list(dict.fromkeys(ocr_result.warnings + (extracted.warnings if extracted else []))),
        "ocr_suggested_amount": float(extracted.amount_total.value) if extracted and extracted.amount_total else None,
        "ocr_suggested_date": extracted.invoice_date.value if extracted and extracted.invoice_date else None,
        "ocr_suggested_supplier": extracted.supplier_name.value if extracted and extracted.supplier_name else None,
        "created_by_user_id": authorized.current.user["user_id"],
        "created_at": now,
        "updated_at": now,
    }
    try:
        get_documents_container().create_item(document_item)
    except Exception as exc:
        logger.error("Voucher metadata write failed after Blob upload: %s", exc)
        try:
            storage_service.delete_file(blob["blob_name"])
        except Exception as cleanup_exc:
            logger.warning("Blob cleanup failed after voucher metadata failure: %s", cleanup_exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kunne ikke lagre bilaget. Prøv igjen.",
        ) from exc

    _write_audit_event("DocumentUploaded", farm_id, authorized.current.user["user_id"])
    return _voucher_response(document_item)


@router.get("/api/farms/{farm_id}/vouchers", response_model=list[VoucherResponse])
async def list_vouchers(
    farm_id: str,
    q: str = Query(default="", max_length=200),
    voucher_status: Optional[str] = Query(default=None, alias="status"),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.VOUCHER_READ)),
) -> list[VoucherResponse]:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fra-dato kan ikke være etter til-dato")
    return [
        _voucher_response(item)
        for item in _list_voucher_items(farm_id)
        if _voucher_matches_filters(item, q=q, voucher_status=voucher_status, date_from=date_from, date_to=date_to)
    ]


@router.get("/api/farms/{farm_id}/vouchers/{voucher_id}", response_model=VoucherResponse)
async def get_voucher(
    farm_id: str,
    voucher_id: str,
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.VOUCHER_READ)),
) -> VoucherResponse:
    return _voucher_response(_read_voucher(farm_id=farm_id, voucher_id=voucher_id))


@router.patch("/api/farms/{farm_id}/vouchers/{voucher_id}", response_model=VoucherResponse)
async def review_voucher(
    farm_id: str,
    voucher_id: str,
    request: ReviewVoucherRequest,
    authorized: AuthorizedFarm = Depends(
        require_farm_permission(Permission.VOUCHER_CREATE, require_csrf_protection=True, require_active_farm=True)
    ),
) -> VoucherResponse:
    """Update user-confirmed fields on a voucher.

    For unbooked vouchers all fields can be updated. For booked vouchers only
    document metadata may change; accounting-critical fields (amount, date,
    account, MVA code) are locked -- corrections go through the correction flow.
    User-confirmed values are authoritative and will not be overwritten by OCR.
    """
    item = _read_voucher(farm_id=farm_id, voucher_id=voucher_id)
    is_booked = item.get("status") == "ført"

    if is_booked:
        # Reject attempts to change accounting-critical fields on booked vouchers.
        locked_changes: list[str] = []
        if request.amount is not None and float(request.amount) != float(item.get("amount") or 0):
            locked_changes.append("beløp")
        if request.voucher_date is not None and request.voucher_date != item.get("voucher_date"):
            locked_changes.append("bilagsdato")
        if request.account_code is not None and request.account_code != item.get("account_code"):
            locked_changes.append("regnskapskonto")
        if request.mva_code is not None and request.mva_code != item.get("mva_code"):
            locked_changes.append("MVA-kode")

        if locked_changes:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Bilaget er bokført. Dokumentinformasjon kan endres, men "
                    f"{', '.join(locked_changes)} krever en egen korrigeringsflyt."
                ),
            )

    now = datetime.now(timezone.utc).isoformat()

    # Accounting-critical fields: only update for unbooked vouchers.
    if not is_booked:
        if request.amount is not None:
            item["amount"] = request.amount
        if request.voucher_date is not None:
            item["voucher_date"] = request.voucher_date
        if request.account_code is not None:
            item["account_code"] = request.account_code
        if request.mva_code is not None:
            item["mva_code"] = request.mva_code

    # Metadata fields: allowed for both booked and unbooked vouchers.
    if request.description is not None:
        item["description"] = request.description
    if request.supplier_name is not None:
        item["supplier_name"] = request.supplier_name
    if request.supplier_org_number is not None:
        item["supplier_org_number"] = request.supplier_org_number
    if request.invoice_number is not None:
        item["invoice_number"] = request.invoice_number
    if request.due_date is not None:
        item["due_date"] = request.due_date
    if request.amount_excluding_vat is not None:
        item["amount_excluding_vat"] = request.amount_excluding_vat
    if request.vat_amount is not None:
        item["vat_amount"] = request.vat_amount
    if request.currency is not None:
        item["currency"] = request.currency
    if request.kid is not None:
        item["kid"] = request.kid
    if request.bank_account is not None:
        item["bank_account"] = request.bank_account
    if request.document_type is not None:
        item["document_type"] = request.document_type

    # Status transitions only apply to unbooked vouchers.
    if not is_booked:
        if request.ready_for_booking:
            required_fields = ["amount", "voucher_date", "account_code", "description"]
            missing_fields = [f for f in required_fields if not item.get(f)]
            if missing_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Manglende påkrevde felt: {', '.join(missing_fields)}"
                )
            item["status"] = "ready"
        elif item.get("status") == "needs_review":
            # Keep in needs_review until explicitly marked ready
            pass

    item["updated_at"] = now

    try:
        get_documents_container().replace_item(item=item["id"], body=item)
    except Exception as exc:
        raise _service_unavailable("Kunne ikke lagre endringene. Prøv igjen.", exc) from exc

    _write_audit_event("VoucherReviewed", farm_id, authorized.current.user["user_id"])
    return _voucher_response(item)


@router.get("/api/farms/{farm_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    farm_id: str,
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.DOCUMENT_READ)),
) -> list[DocumentResponse]:
    return [_document_response(item) for item in _list_voucher_items(farm_id)]


@router.get("/api/farms/{farm_id}/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    farm_id: str,
    document_id: str,
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.DOCUMENT_READ)),
) -> DocumentResponse:
    return _document_response(_read_document(farm_id=farm_id, document_id=document_id))


@router.get("/api/farms/{farm_id}/documents/{document_id}/download")
async def download_document(
    farm_id: str,
    document_id: str,
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.DOCUMENT_DOWNLOAD)),
) -> StreamingResponse:
    """Authorize metadata first, then stream one private Blob through the API."""
    document = _read_document(farm_id=farm_id, document_id=document_id)
    blob_name = str(document.get("blob_name") or "")
    if not blob_name:
        # A legacy direct URL is deliberately not a fallback authorization mechanism.
        raise _resource_not_found()
    try:
        payload = storage_service.download_file(blob_name)
    except Exception as exc:
        raise _service_unavailable("Dokumentet er midlertidig utilgjengelig. Prøv igjen.", exc) from exc

    file_name = str(document.get("file_name") or "dokument")
    return StreamingResponse(
        iter([payload]),
        media_type=str(document.get("content_type") or "application/octet-stream"),
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(file_name, safe='')}",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/api/farms/{farm_id}/vouchers/{voucher_id}/book", response_model=VoucherResponse)
async def book_voucher(
    farm_id: str,
    voucher_id: str,
    request: BookVoucherRequest,
    authorized: AuthorizedFarm = Depends(
        require_farm_permission(Permission.VOUCHER_BOOK, require_csrf_protection=True, require_active_farm=True)
    ),
) -> VoucherResponse:
    """Book one voucher as a balanced double-entry journal posting.

    Uses user-confirmed values from the voucher document. The request can
    override specific fields, but typically the already-reviewed voucher values
    are used. No legacy accounting_transaction document is created.
    """
    if request.transaction_type not in {"income", "expense"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="transaction_type må være income eller expense")
    item = _read_voucher(farm_id=farm_id, voucher_id=voucher_id)
    if item.get("status") == "ført":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bilaget er allerede ført.")

    # Use user-confirmed values from voucher unless explicitly overridden in request
    amount = request.amount if request.amount is not None else item.get("amount", 0.0)
    account_code = request.account_code if request.account_code else item.get("account_code")
    mva_code = request.mva_code if request.mva_code is not None else item.get("mva_code")
    description = request.description if request.description is not None else item.get("description", "")
    voucher_date = request.voucher_date or item.get("voucher_date") or datetime.now(timezone.utc).date().isoformat()

    # Validate required fields for booking
    if not account_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Regnskapskonto er påkrevd for bokføring.")
    if not amount or amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Beløp må være større enn null.")

    try:
        entry = accounting_posting_service.post_voucher_booking(
            farm_id=farm_id,
            voucher=item,
            transaction_type=request.transaction_type,
            account_code=account_code,
            counter_account_code=request.counter_account_code,
            vat_code=mva_code,
            amount=amount,
            amount_excluding_vat=item.get("amount_excluding_vat"),
            vat_amount=item.get("vat_amount"),
            description=description,
            posting_date=voucher_date,
            user_id=authorized.current.user["user_id"],
            vat_registered=_farm_is_vat_registered(farm_id),
        )
    except Exception as exc:
        raise _journal_error_response(exc) from exc

    now = datetime.now(timezone.utc).isoformat()
    item.update(
        {
            "amount": amount,
            "account_code": account_code,
            "mva_code": mva_code,
            "status": "ført",
            "description": description,
            "voucher_date": voucher_date,
            "journal_entry_id": entry.get("id"),
            "journal_number": entry.get("journal_number"),
            "accounting_revision": 1,
            "updated_at": now,
        }
    )
    try:
        get_documents_container().upsert_item(item)
    except Exception as exc:
        # The journal entry is authoritative; do not delete it. Retry/reconcile
        # can complete the voucher metadata later.
        logger.error(
            "Voucher metadata update failed after journal posting %s: %s",
            entry.get("journal_number"),
            exc,
        )

    _write_audit_event("JournalEntryPosted", farm_id, authorized.current.user["user_id"])
    return _voucher_response(item)


@router.post("/api/farms/{farm_id}/vouchers/{voucher_id}/correct-booking", response_model=VoucherResponse)
async def correct_voucher_booking(
    farm_id: str,
    voucher_id: str,
    request: CorrectBookingRequest,
    authorized: AuthorizedFarm = Depends(
        require_farm_permission(Permission.JOURNAL_CORRECT, require_csrf_protection=True, require_active_farm=True)
    ),
) -> VoucherResponse:
    """Correct a booked voucher by posting a new balanced correction entry.

    The original journal entry is never mutated. The correction reverses the
    current effective accounting state and posts the corrected effect in one
    balanced entry with its own journal number.
    """
    if request.transaction_type not in {"income", "expense"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="transaction_type må være income eller expense")
    if not (request.reason or "").strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Begrunnelse for korrigeringen er påkrevd.")

    item = _read_voucher(farm_id=farm_id, voucher_id=voucher_id)
    if item.get("status") != "ført":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bilaget er ikke bokført og kan ikke korrigeres.")

    try:
        entry = accounting_posting_service.post_voucher_correction(
            farm_id=farm_id,
            voucher=item,
            transaction_type=request.transaction_type,
            account_code=request.account_code,
            counter_account_code=request.counter_account_code,
            vat_code=request.mva_code,
            amount=request.amount,
            amount_excluding_vat=request.amount_excluding_vat,
            vat_amount=request.vat_amount,
            description=request.description or item.get("description") or "",
            correction_date=request.correction_date,
            reason=request.reason.strip(),
            user_id=authorized.current.user["user_id"],
            vat_registered=_farm_is_vat_registered(farm_id),
        )
    except Exception as exc:
        raise _journal_error_response(exc) from exc

    now = datetime.now(timezone.utc).isoformat()
    item.update(
        {
            "amount": request.amount,
            "account_code": request.account_code,
            "mva_code": request.mva_code,
            "description": request.description if request.description is not None else item.get("description"),
            "journal_entry_id": entry.get("id"),
            "journal_number": entry.get("journal_number"),
            "accounting_revision": int(entry.get("source_revision") or 2),
            "updated_at": now,
        }
    )
    if request.amount_excluding_vat is not None:
        item["amount_excluding_vat"] = request.amount_excluding_vat
    if request.vat_amount is not None:
        item["vat_amount"] = request.vat_amount
    try:
        get_documents_container().upsert_item(item)
    except Exception as exc:
        # Journal is authoritative; metadata can be reconciled on retry.
        logger.error(
            "Voucher metadata update failed after correction %s: %s",
            entry.get("journal_number"),
            exc,
        )

    _write_audit_event("VoucherAccountingCorrected", farm_id, authorized.current.user["user_id"])
    return _voucher_response(item)


@router.get("/api/farms/{farm_id}/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    farm_id: str,
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.TRANSACTION_READ)),
) -> list[TransactionResponse]:
    """DEPRECATED compatibility projection.

    New bookings never write accounting_transaction documents. This endpoint
    keeps returning legacy transactions for existing clients; journal entries
    are the source of truth and win over duplicates.
    """
    journal_source_keys = {
        entry.get("source_key")
        for entry in journal_service.list_entries(farm_id, source_type="voucher", limit=5000)
    }
    rows: list[TransactionResponse] = []
    for item in _fetch_legacy_transactions(farm_id):
        # Skip legacy rows that already have a journal posting for the same voucher.
        if f"voucher:{item.get('voucher_id')}:booking" in journal_source_keys:
            continue
        rows.append(_transaction_response(item))
    return rows


# ---------------------------------------------------------------------------
# Journal API
# ---------------------------------------------------------------------------

@router.get("/api/farms/{farm_id}/journal")
async def list_journal_entries(
    farm_id: str,
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    account_code: Optional[str] = Query(default=None),
    source_type: Optional[str] = Query(default=None),
    source_id: Optional[str] = Query(default=None),
    journal_number: Optional[str] = Query(default=None),
    limit: int = Query(default=200, le=1000),
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.JOURNAL_READ)),
) -> dict[str, Any]:
    entries = journal_service.list_entries(
        farm_id,
        date_from=date_from,
        date_to=date_to,
        account_code=account_code,
        source_type=source_type,
        source_id=source_id,
        journal_number=journal_number,
        limit=limit,
    )
    return {"entries": entries}


@router.get("/api/farms/{farm_id}/journal/{entry_id}")
async def get_journal_entry(
    farm_id: str,
    entry_id: str,
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.JOURNAL_READ)),
) -> dict[str, Any]:
    entry = journal_service.read_entry(farm_id, entry_id)
    if not entry:
        raise _resource_not_found()
    return entry


# ---------------------------------------------------------------------------
# Accounting periods
# ---------------------------------------------------------------------------

def _read_period(farm_id: str, period: str) -> Optional[dict[str, Any]]:
    from app.db.cosmos_client import get_accounting_periods_container

    try:
        return get_accounting_periods_container().read_item(
            item=f"accounting-period:{farm_id}:{period}",
            partition_key=farm_id,
        )
    except exceptions.CosmosResourceNotFoundError:
        return None


@router.get("/api/farms/{farm_id}/accounting/periods")
async def list_accounting_periods(
    farm_id: str,
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.ACCOUNTING_PERIOD_READ)),
) -> dict[str, Any]:
    """List periods derived from journal activity plus explicit period documents."""
    entries = journal_service.list_entries(farm_id, limit=5000)
    seen: set[str] = set()
    for entry in entries:
        period = str(entry.get("posting_date") or "")[:7]
        if period:
            seen.add(period)

    from app.db.cosmos_client import get_accounting_periods_container

    try:
        period_docs = list(
            get_accounting_periods_container().query_items(
                query="SELECT * FROM c WHERE c.type = 'accounting_period' AND c.farm_id = @farm_id",
                parameters=[{"name": "@farm_id", "value": farm_id}],
                partition_key=farm_id,
            )
        )
    except Exception:
        period_docs = []
    for doc in period_docs:
        if doc.get("period"):
            seen.add(doc["period"])

    rows = []
    for period in sorted(seen, reverse=True):
        doc = _read_period(farm_id, period)
        rows.append(
            {
                "period": period,
                "status": doc.get("status") if doc else "open",
                "locked_at": doc.get("locked_at") if doc else None,
                "locked_by_user_id": doc.get("locked_by_user_id") if doc else None,
            }
        )
    return {"periods": rows}


@router.post("/api/farms/{farm_id}/accounting/periods/{period}/lock")
async def lock_accounting_period(
    farm_id: str,
    period: str,
    authorized: AuthorizedFarm = Depends(
        require_farm_permission(Permission.ACCOUNTING_PERIOD_LOCK, require_csrf_protection=True, require_active_farm=True)
    ),
) -> dict[str, Any]:
    from app.db.cosmos_client import get_accounting_periods_container

    try:
        date.fromisoformat(f"{period}-01")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ugyldig periodeformat. Bruk YYYY-MM.") from exc

    doc = {
        "id": f"accounting-period:{farm_id}:{period}",
        "type": "accounting_period",
        "farm_id": farm_id,
        "period": period,
        "status": "locked",
        "locked_at": datetime.now(timezone.utc).isoformat(),
        "locked_by_user_id": authorized.current.user["user_id"],
    }
    try:
        get_accounting_periods_container().upsert_item(doc)
    except Exception as exc:
        raise _service_unavailable("Kunne ikke låse perioden. Prøv igjen.", exc) from exc

    _write_audit_event("AccountingPeriodLocked", farm_id, authorized.current.user["user_id"])
    return doc


@router.post("/api/farms/{farm_id}/accounting/periods/{period}/unlock")
async def unlock_accounting_period(
    farm_id: str,
    period: str,
    authorized: AuthorizedFarm = Depends(
        require_farm_permission(Permission.ACCOUNTING_PERIOD_UNLOCK, require_csrf_protection=True, require_active_farm=True)
    ),
) -> dict[str, Any]:
    from app.db.cosmos_client import get_accounting_periods_container

    doc = _read_period(farm_id, period)
    if not doc:
        raise _resource_not_found()
    doc["status"] = "open"
    doc["unlocked_at"] = datetime.now(timezone.utc).isoformat()
    doc["unlocked_by_user_id"] = authorized.current.user["user_id"]
    try:
        get_accounting_periods_container().upsert_item(doc)
    except Exception as exc:
        raise _service_unavailable("Kunne ikke låse opp perioden. Prøv igjen.", exc) from exc

    _write_audit_event("AccountingPeriodUnlocked", farm_id, authorized.current.user["user_id"])
    return doc


# ---------------------------------------------------------------------------
# Reports (journal-based)
# ---------------------------------------------------------------------------

@router.get("/api/farms/{farm_id}/reports/monthly")
async def report_monthly(
    farm_id: str,
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.REPORT_BASIC_READ)),
) -> dict[str, Any]:
    """Monthly result from journal lines using account metadata.

    Income = credits - debits on income accounts; expense = debits - credits on
    expense accounts. Corrections affect the result automatically.
    """
    monthly: dict[str, dict[str, int]] = defaultdict(lambda: {"income": 0, "expense": 0})
    for entry in journal_service.list_entries(farm_id, limit=5000):
        month = str(entry.get("posting_date") or "")[:7]
        if not month:
            continue
        for line in entry.get("lines", []):
            account = get_account(line.get("account_code"))
            if not account:
                continue
            debit = int(line.get("debit_ore") or 0)
            credit = int(line.get("credit_ore") or 0)
            if account.get("account_type") == "income":
                monthly[month]["income"] += credit - debit
            elif account.get("account_type") == "expense":
                monthly[month]["expense"] += debit - credit
    return {
        "rows": [
            {
                "month": key,
                "income": round(ore_to_kroner(values["income"]), 2),
                "expense": round(ore_to_kroner(values["expense"]), 2),
                "net": round(ore_to_kroner(values["income"] - values["expense"]), 2),
            }
            for key, values in sorted(monthly.items())
        ]
    }


@router.get("/api/farms/{farm_id}/reports/vat")
async def report_vat(
    farm_id: str,
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.REPORT_BASIC_READ)),
) -> dict[str, Any]:
    """VAT report from actual VAT journal lines (2710 input / 2700 output)."""
    incoming_ore = 0
    outgoing_ore = 0
    for entry in journal_service.list_entries(farm_id, limit=5000):
        for line in entry.get("lines", []):
            account_code = line.get("account_code")
            vat_amount = int(line.get("vat_amount_ore") or 0)
            if vat_amount <= 0:
                continue
            if account_code == "2710":
                incoming_ore += vat_amount
            elif account_code == "2700":
                outgoing_ore += vat_amount
    return {
        "incoming_vat": round(ore_to_kroner(incoming_ore), 2),
        "outgoing_vat": round(ore_to_kroner(outgoing_ore), 2),
        "estimated_settlement": round(ore_to_kroner(outgoing_ore - incoming_ore), 2),
    }


@router.get("/api/farms/{farm_id}/reports/grants")
async def report_grants(
    farm_id: str,
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.REPORT_BASIC_READ)),
) -> dict[str, Any]:
    """Grants identified primarily from account 3100 in journal lines."""
    rows = []
    for entry in journal_service.list_entries(farm_id, limit=5000):
        posting_date = str(entry.get("posting_date") or "")
        for line in entry.get("lines", []):
            if line.get("account_code") != "3100":
                continue
            amount_ore = int(line.get("credit_ore") or 0) - int(line.get("debit_ore") or 0)
            if amount_ore <= 0:
                continue
            rows.append(
                {
                    "voucher_date": posting_date,
                    "amount": round(ore_to_kroner(amount_ore), 2),
                    "description": line.get("description") or entry.get("description") or "Tilskudd",
                    "period": posting_date[:7],
                }
            )
    return {"rows": sorted(rows, key=lambda item: item["voucher_date"], reverse=True)}


@router.get("/api/farms/{farm_id}/reports/journal")
async def report_journal(
    farm_id: str,
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.REPORT_BASIC_READ)),
) -> dict[str, Any]:
    """The actual double-entry journal, not voucher metadata."""
    rows = []
    for entry in journal_service.list_entries(farm_id, limit=5000):
        rows.append(
            {
                "journal_entry_id": entry.get("id"),
                "journal_number": entry.get("journal_number"),
                "posting_date": entry.get("posting_date"),
                "source_type": entry.get("source_type"),
                "source_id": entry.get("source_id"),
                "description": entry.get("description"),
                "total_debit": round(ore_to_kroner(int(entry.get("total_debit_ore") or 0)), 2),
                "total_credit": round(ore_to_kroner(int(entry.get("total_credit_ore") or 0)), 2),
                "is_correction": bool(entry.get("correction_of")),
            }
        )
    return {"rows": rows}


@router.get("/api/farms/{farm_id}/reports/liquidity")
async def report_liquidity(
    farm_id: str,
    opening_balance: float = Query(default=0.0),
    _: AuthorizedEntitlement = Depends(
        require_entitlement(
            "reports.advanced.enabled",
            permission=Permission.REPORT_ADVANCED_READ,
            access_mode="read",
        )
    ),
) -> dict[str, Any]:
    """Liquidity from cash/bank account movements only.

    Issued-but-unpaid invoices do not affect liquidity; payments do.
    """
    balance_ore = int(round(opening_balance * 100))
    movements: list[tuple[str, str, int]] = []
    for entry in journal_service.list_entries(farm_id, limit=5000):
        posting_date = str(entry.get("posting_date") or "")
        for line in entry.get("lines", []):
            if not is_cash_account(line.get("account_code")):
                continue
            delta = int(line.get("debit_ore") or 0) - int(line.get("credit_ore") or 0)
            if delta == 0:
                continue
            movements.append((posting_date, line.get("description") or entry.get("description") or "Bilag", delta))

    points = []
    for posting_date, description, delta in sorted(movements, key=lambda item: item[0]):
        balance_ore += delta
        points.append(
            {
                "date": posting_date,
                "description": description,
                "balance": round(ore_to_kroner(balance_ore), 2),
            }
        )
    return {
        "opening_balance": opening_balance,
        "closing_balance": round(ore_to_kroner(balance_ore), 2),
        "points": points,
    }


@router.get("/api/farms/{farm_id}/reports/trial-balance")
async def report_trial_balance(
    farm_id: str,
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.REPORT_BASIC_READ)),
) -> dict[str, Any]:
    """Per-account debit/credit/balance from the journal. Total must balance."""
    accounts: dict[str, dict[str, int]] = defaultdict(lambda: {"debit": 0, "credit": 0})
    for entry in journal_service.list_entries(farm_id, limit=5000):
        for line in entry.get("lines", []):
            code = str(line.get("account_code") or "")
            if not code:
                continue
            accounts[code]["debit"] += int(line.get("debit_ore") or 0)
            accounts[code]["credit"] += int(line.get("credit_ore") or 0)

    rows = []
    total_debit = 0
    total_credit = 0
    for code in sorted(accounts.keys()):
        values = accounts[code]
        account = get_account(code) or {}
        debit = values["debit"]
        credit = values["credit"]
        total_debit += debit
        total_credit += credit
        rows.append(
            {
                "account_code": code,
                "account_name": account.get("name") or "",
                "account_type": account.get("account_type") or "",
                "debit": round(ore_to_kroner(debit), 2),
                "credit": round(ore_to_kroner(credit), 2),
                "balance": round(ore_to_kroner(debit - credit), 2),
            }
        )
    return {
        "rows": rows,
        "total_debit": round(ore_to_kroner(total_debit), 2),
        "total_credit": round(ore_to_kroner(total_credit), 2),
        "balanced": total_debit == total_credit,
    }