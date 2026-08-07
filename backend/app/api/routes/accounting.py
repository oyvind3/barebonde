"""Tenant-scoped voucher, document, transaction, and reporting routes."""

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
    get_transactions_container,
)
from app.services.accounting_catalog import GLOSSARY, search_accounts
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


def _fetch_transactions(farm_id: str) -> list[dict[str, Any]]:
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
            "currency": ocr_service._field_to_dict(extracted.currency) if extracted and extracted.currency else None,
            "kid": ocr_service._field_to_dict(extracted.kid) if extracted and extracted.kid else None,
            "bank_account": ocr_service._field_to_dict(extracted.bank_account) if extracted and extracted.bank_account else None,
        } if extracted else {},
        # Legacy fields for backward compatibility
        "simple_mode": bool(simple_mode),
        "ocr_provider": ocr_result.provider,
        "ocr_confidence": ocr_result.confidence,
        "ocr_text_preview": extracted.text_preview if extracted else None,
        "ocr_warnings": ocr_result.warnings,
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
    """Update user-confirmed fields on an unbooked voucher.
    
    This endpoint allows users to correct OCR suggestions before booking.
    User-confirmed values are authoritative and will not be overwritten by OCR.
    The voucher status is updated to 'ready' when all required fields are set.
    """
    item = _read_voucher(farm_id=farm_id, voucher_id=voucher_id)
    
    if item.get("status") == "ført":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bilaget er allerede ført og kan ikke endres.")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update only fields provided in the request (partial update)
    if request.amount is not None:
        item["amount"] = request.amount
    if request.voucher_date is not None:
        item["voucher_date"] = request.voucher_date
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
    if request.account_code is not None:
        item["account_code"] = request.account_code
    if request.mva_code is not None:
        item["mva_code"] = request.mva_code
    
    # Update status based on ready_for_booking flag or field completeness
    if request.ready_for_booking:
        # Validate required fields before marking as ready
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
    """Book one voucher and atomically-as-practical create its transaction.
    
    Uses user-confirmed values from the voucher document. The request can override
    specific fields, but typically the already-reviewed voucher values are used.
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
    voucher_date = item.get("voucher_date") or datetime.now(timezone.utc).date().isoformat()
    
    # Validate required fields for booking
    if not account_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Regnskapskonto er påkrevd for bokføring.")
    if not amount or amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Beløp må være større enn null.")
    
    now = datetime.now(timezone.utc).isoformat()
    transaction_item = {
        "id": f"transaction:{voucher_id}",
        "type": "accounting_transaction",
        "farm_id": farm_id,
        "voucher_id": voucher_id,
        "transaction_type": request.transaction_type,
        "category": request.category or "Drift",
        "amount": amount,
        "account_code": account_code,
        "mva_code": mva_code,
        "description": description,
        "voucher_date": voucher_date,
        "created_by_user_id": authorized.current.user["user_id"],
        "created_at": now,
    }
    try:
        get_transactions_container().create_item(transaction_item)
    except exceptions.CosmosResourceExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bilaget er allerede ført.") from exc
    except Exception as exc:
        raise _service_unavailable("Kunne ikke føre bilaget. Prøv igjen.", exc) from exc

    item.update(
        {
            "amount": amount,
            "account_code": account_code,
            "mva_code": mva_code,
            "status": "ført",
            "description": description,
            "updated_at": now,
        }
    )
    try:
        get_documents_container().upsert_item(item)
    except Exception as exc:
        logger.error("Voucher booking metadata update failed after transaction creation: %s", exc)
        try:
            get_transactions_container().delete_item(item=transaction_item["id"], partition_key=farm_id)
        except Exception as cleanup_exc:
            logger.warning("Transaction cleanup failed after voucher booking failure: %s", cleanup_exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kunne ikke føre bilaget. Prøv igjen.",
        ) from exc

    _write_audit_event("VoucherBooked", farm_id, authorized.current.user["user_id"])
    return _voucher_response(item)


@router.get("/api/farms/{farm_id}/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    farm_id: str,
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.TRANSACTION_READ)),
) -> list[TransactionResponse]:
    return [_transaction_response(item) for item in _fetch_transactions(farm_id)]


@router.get("/api/farms/{farm_id}/reports/monthly")
async def report_monthly(
    farm_id: str,
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.REPORT_BASIC_READ)),
) -> dict[str, Any]:
    monthly: dict[str, dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    for tx in _fetch_transactions(farm_id):
        key = _month_key(str(tx.get("voucher_date") or ""))
        amount = float(tx.get("amount") or 0)
        monthly[key]["income" if tx.get("transaction_type") == "income" else "expense"] += amount
    return {
        "rows": [
            {"month": key, "income": values["income"], "expense": values["expense"], "net": values["income"] - values["expense"]}
            for key, values in sorted(monthly.items())
        ]
    }


@router.get("/api/farms/{farm_id}/reports/vat")
async def report_vat(
    farm_id: str,
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.REPORT_BASIC_READ)),
) -> dict[str, Any]:
    incoming_vat = 0.0
    outgoing_vat = 0.0
    for tx in _fetch_transactions(farm_id):
        amount = float(tx.get("amount") or 0)
        mva_code = str(tx.get("mva_code") or "").lower()
        rate = 0.15 if "15" in mva_code else 0.12 if "12" in mva_code else 0.0 if "0" in mva_code else 0.25
        if tx.get("transaction_type") == "income":
            outgoing_vat += amount * rate
        elif "fradrag" in mva_code or mva_code in {"25", "15", "12"}:
            incoming_vat += amount * rate
    return {
        "incoming_vat": round(incoming_vat, 2),
        "outgoing_vat": round(outgoing_vat, 2),
        "estimated_settlement": round(outgoing_vat - incoming_vat, 2),
    }


@router.get("/api/farms/{farm_id}/reports/grants")
async def report_grants(
    farm_id: str,
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.REPORT_BASIC_READ)),
) -> dict[str, Any]:
    rows = []
    for tx in _fetch_transactions(farm_id):
        description = str(tx.get("description") or "")
        if tx.get("account_code") == "3100" or "tilskudd" in description.casefold():
            voucher_date = str(tx.get("voucher_date") or datetime.now(timezone.utc).date().isoformat())
            rows.append({"voucher_date": voucher_date, "amount": float(tx.get("amount") or 0), "description": description or "Tilskudd", "period": _month_key(voucher_date)})
    return {"rows": sorted(rows, key=lambda item: item["voucher_date"], reverse=True)}


@router.get("/api/farms/{farm_id}/reports/journal")
async def report_journal(
    farm_id: str,
    _: AuthorizedFarm = Depends(require_farm_permission(Permission.REPORT_BASIC_READ)),
) -> dict[str, Any]:
    return {
        "rows": [
            {
                "voucher_id": item["id"],
                "date": item.get("voucher_date"),
                "file_name": item.get("file_name"),
                "status": item.get("status") or "mottatt",
                "account_code": item.get("account_code"),
                "mva_code": item.get("mva_code"),
                "amount": float(item.get("amount") or 0),
            }
            for item in _list_voucher_items(farm_id)
        ]
    }


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
    balance = opening_balance
    points = []
    for tx in sorted(_fetch_transactions(farm_id), key=lambda item: str(item.get("voucher_date") or "")):
        amount = float(tx.get("amount") or 0)
        balance += amount if tx.get("transaction_type") == "income" else -amount
        points.append(
            {
                "date": tx.get("voucher_date"),
                "description": tx.get("description") or tx.get("category") or "Bilag",
                "balance": round(balance, 2),
            }
        )
    return {"opening_balance": opening_balance, "closing_balance": round(balance, 2), "points": points}
