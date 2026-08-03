"""Accounting routes for bilag upload, posting, and reports."""

from collections import defaultdict
from datetime import date, datetime
from typing import Any, Optional
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from app.db.cosmos_client import get_documents_container, get_transactions_container
from app.services.accounting_catalog import GLOSSARY, search_accounts
from app.services.ocr_service import ocr_service
from app.services.storage_service import storage_service

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


class VoucherResponse(BaseModel):
    id: str
    farm_id: str
    file_name: str
    content_type: str
    status: str
    amount: float
    account_code: Optional[str]
    mva_code: Optional[str]
    voucher_date: str
    description: Optional[str]
    blob_url: str
    ocr_text_preview: Optional[str] = None
    ocr_provider: Optional[str] = None
    ocr_confidence: Optional[float] = None
    ocr_suggested_amount: Optional[float] = None
    ocr_suggested_date: Optional[str] = None
    ocr_suggested_supplier: Optional[str] = None


class BookVoucherRequest(BaseModel):
    amount: float
    account_code: str
    mva_code: Optional[str] = None
    transaction_type: str = "expense"
    category: Optional[str] = None
    description: Optional[str] = None


def _validate_file(content_type: str, size_bytes: int, file_name: str) -> None:
    extension = ""
    if "." in file_name:
        extension = file_name.rsplit(".", 1)[-1].lower()

    content_type_allowed = content_type in ALLOWED_CONTENT_TYPES
    extension_allowed = extension in ALLOWED_EXTENSIONS

    if not content_type_allowed and not extension_allowed and content_type != "application/octet-stream":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filtype støttes ikke. Bruk bilde, PDF eller tekstbasert fil (txt/csv/json/xml).",
        )

    if content_type == "application/octet-stream" and not extension_allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ukjent binærfil. Bruk bilde, PDF eller tekstfil med kjent filendelse.",
        )

    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filen er for stor. Maks størrelse er 15 MB.",
        )


@router.post("/vouchers/upload", response_model=VoucherResponse)
async def upload_voucher(
    file: UploadFile = File(...),
    farm_id: str = Form(...),
    description: Optional[str] = Form(default=None),
    voucher_date: Optional[str] = Form(default=None),
    simple_mode: bool = Form(default=False),
) -> VoucherResponse:
    """Upload bilag file (image/pdf) and create voucher metadata."""
    content = await file.read()
    _validate_file(file.content_type or "", len(content), file.filename or "")

    try:
        blob = storage_service.upload_file(
            farm_id=farm_id,
            file_name=file.filename or "bilag",
            content_type=file.content_type or "application/octet-stream",
            payload=content,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Filopplasting er ikke konfigurert enda. Sett opp Azure Storage.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Klarte ikke laste opp bilag: {exc}",
        ) from exc

    document_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    effective_date = voucher_date or datetime.utcnow().date().isoformat()
    file_name = file.filename or "bilag"

    ocr_result = ocr_service.extract_text(
        payload=content,
        content_type=file.content_type or "",
        file_name=file_name,
    )
    inferred_fields = ocr_service.infer_fields(ocr_result.text)

    document_item = {
        "id": document_id,
        "type": "voucher_document",
        "farm_id": farm_id,
        "file_name": file_name,
        "content_type": file.content_type,
        "size_bytes": blob["size_bytes"],
        "blob_name": blob["blob_name"],
        "blob_url": blob["blob_url"],
        "description": description or inferred_fields.get("suggested_supplier") or "",
        "simple_mode": bool(simple_mode),
        "status": "mottatt",
        "account_code": None,
        "mva_code": None,
        "amount": float(inferred_fields.get("suggested_amount") or 0.0),
        "voucher_date": inferred_fields.get("suggested_date") or effective_date,
        "ocr_provider": ocr_result.provider,
        "ocr_confidence": ocr_result.confidence,
        "ocr_text_preview": inferred_fields.get("text_preview"),
        "ocr_warnings": ocr_result.warnings,
        "ocr_suggested_amount": inferred_fields.get("suggested_amount"),
        "ocr_suggested_date": inferred_fields.get("suggested_date"),
        "ocr_suggested_supplier": inferred_fields.get("suggested_supplier"),
        "created_at": now,
        "updated_at": now,
    }

    get_documents_container().upsert_item(document_item)

    return VoucherResponse(**{
        "id": document_id,
        "farm_id": farm_id,
        "file_name": document_item["file_name"],
        "content_type": document_item["content_type"],
        "status": document_item["status"],
        "amount": float(document_item["amount"]),
        "account_code": document_item["account_code"],
        "mva_code": document_item["mva_code"],
        "voucher_date": document_item["voucher_date"],
        "description": document_item["description"],
        "blob_url": document_item["blob_url"],
        "ocr_text_preview": document_item.get("ocr_text_preview"),
        "ocr_provider": document_item.get("ocr_provider"),
        "ocr_confidence": document_item.get("ocr_confidence"),
        "ocr_suggested_amount": document_item.get("ocr_suggested_amount"),
        "ocr_suggested_date": document_item.get("ocr_suggested_date"),
        "ocr_suggested_supplier": document_item.get("ocr_suggested_supplier"),
    })


@router.get("/vouchers", response_model=list[VoucherResponse])
async def list_vouchers(
    farm_id: str = Query(...),
    q: str = Query(default="", max_length=200),
    voucher_status: Optional[str] = Query(default=None, alias="status"),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
) -> list[VoucherResponse]:
    """List and filter vouchers for a farm."""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fra-dato kan ikke være etter til-dato",
        )

    query = "SELECT * FROM c WHERE c.farm_id = @farm_id AND c.type = 'voucher_document' ORDER BY c.created_at DESC"
    items = list(
        get_documents_container().query_items(
            query=query,
            parameters=[{"name": "@farm_id", "value": farm_id}],
            enable_cross_partition_query=True,
        )
    )
    items = [
        item
        for item in items
        if _voucher_matches_filters(
            item,
            q=q,
            voucher_status=voucher_status,
            date_from=date_from,
            date_to=date_to,
        )
    ]

    return [
        VoucherResponse(
            id=item["id"],
            farm_id=item["farm_id"],
            file_name=item["file_name"],
            content_type=item.get("content_type") or "",
            status=item.get("status") or "mottatt",
            amount=float(item.get("amount") or 0),
            account_code=item.get("account_code"),
            mva_code=item.get("mva_code"),
            voucher_date=item.get("voucher_date") or datetime.utcnow().date().isoformat(),
            description=item.get("description"),
            blob_url=item.get("blob_url") or "",
            ocr_text_preview=item.get("ocr_text_preview"),
            ocr_provider=item.get("ocr_provider"),
            ocr_confidence=item.get("ocr_confidence"),
            ocr_suggested_amount=item.get("ocr_suggested_amount"),
            ocr_suggested_date=item.get("ocr_suggested_date"),
            ocr_suggested_supplier=item.get("ocr_suggested_supplier"),
        )
        for item in items
    ]


def _voucher_matches_filters(
    item: dict[str, Any],
    *,
    q: str = "",
    voucher_status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> bool:
    """Apply additive voucher filters after the farm-scoped Cosmos query."""
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
    searchable_text = " ".join(str(value) for value in searchable_fields if value).casefold()
    return normalized_query in searchable_text


@router.post("/vouchers/{voucher_id}/book", response_model=VoucherResponse)
async def book_voucher(voucher_id: str, request: BookVoucherRequest) -> VoucherResponse:
    """Book a voucher by assigning account, VAT, and amount."""
    query = "SELECT * FROM c WHERE c.id = @id AND c.type = 'voucher_document'"
    items = list(
        get_documents_container().query_items(
            query=query,
            parameters=[{"name": "@id", "value": voucher_id}],
            enable_cross_partition_query=True,
        )
    )

    if not items:
        raise HTTPException(status_code=404, detail="Bilaget ble ikke funnet")

    item = items[0]
    if request.transaction_type not in {"income", "expense"}:
        raise HTTPException(status_code=400, detail="transaction_type må være income eller expense")

    item["amount"] = request.amount
    item["account_code"] = request.account_code
    item["mva_code"] = request.mva_code
    item["status"] = "ført"
    item["description"] = request.description or item.get("description") or ""
    item["updated_at"] = datetime.utcnow().isoformat()

    get_documents_container().upsert_item(item)

    transaction_item = {
        "id": str(uuid.uuid4()),
        "type": "accounting_transaction",
        "farm_id": item["farm_id"],
        "voucher_id": voucher_id,
        "transaction_type": request.transaction_type,
        "category": request.category or "Drift",
        "amount": request.amount,
        "account_code": request.account_code,
        "mva_code": request.mva_code,
        "description": request.description or item.get("description") or "",
        "voucher_date": item.get("voucher_date") or datetime.utcnow().date().isoformat(),
        "created_at": datetime.utcnow().isoformat(),
    }
    get_transactions_container().upsert_item(transaction_item)

    return VoucherResponse(
        id=item["id"],
        farm_id=item["farm_id"],
        file_name=item["file_name"],
        content_type=item.get("content_type") or "",
        status=item.get("status") or "ført",
        amount=float(item.get("amount") or 0),
        account_code=item.get("account_code"),
        mva_code=item.get("mva_code"),
        voucher_date=item.get("voucher_date") or datetime.utcnow().date().isoformat(),
        description=item.get("description"),
        blob_url=item.get("blob_url") or "",
        ocr_text_preview=item.get("ocr_text_preview"),
        ocr_provider=item.get("ocr_provider"),
        ocr_confidence=item.get("ocr_confidence"),
        ocr_suggested_amount=item.get("ocr_suggested_amount"),
        ocr_suggested_date=item.get("ocr_suggested_date"),
        ocr_suggested_supplier=item.get("ocr_suggested_supplier"),
    )


@router.get("/accounts")
async def get_accounts(
    query: str = Query(default=""),
    simple_mode: bool = Query(default=False),
) -> dict[str, Any]:
    """Get account list/search results and compact glossary."""
    return {
        "accounts": search_accounts(query=query, simple_mode=simple_mode),
        "glossary": GLOSSARY,
    }


def _fetch_transactions(farm_id: str) -> list[dict[str, Any]]:
    query = "SELECT * FROM c WHERE c.farm_id = @farm_id AND c.type = 'accounting_transaction'"
    return list(
        get_transactions_container().query_items(
            query=query,
            parameters=[{"name": "@farm_id", "value": farm_id}],
            enable_cross_partition_query=True,
        )
    )


def _month_key(date_value: str) -> str:
    try:
        dt = datetime.fromisoformat(date_value)
    except ValueError:
        dt = datetime.utcnow()
    return f"{dt.year}-{dt.month:02d}"


@router.get("/reports/monthly")
async def report_monthly(farm_id: str = Query(...)) -> dict[str, Any]:
    """Monthly result report: income, expense, and net by month."""
    monthly: dict[str, dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expense": 0.0})

    for tx in _fetch_transactions(farm_id):
        key = _month_key(tx.get("voucher_date", datetime.utcnow().isoformat()))
        tx_type = tx.get("transaction_type", "expense")
        amount = float(tx.get("amount") or 0)
        if tx_type == "income":
            monthly[key]["income"] += amount
        else:
            monthly[key]["expense"] += amount

    rows = []
    for key in sorted(monthly.keys()):
        income = monthly[key]["income"]
        expense = monthly[key]["expense"]
        rows.append({"month": key, "income": income, "expense": expense, "net": income - expense})

    return {"rows": rows}


@router.get("/reports/vat")
async def report_vat(farm_id: str = Query(...)) -> dict[str, Any]:
    """VAT base summary report."""
    incoming_vat = 0.0
    outgoing_vat = 0.0

    for tx in _fetch_transactions(farm_id):
        amount = float(tx.get("amount") or 0)
        tx_type = tx.get("transaction_type", "expense")
        mva_code = (tx.get("mva_code") or "").lower()

        if tx_type == "income":
            if "15" in mva_code:
                outgoing_vat += amount * 0.15
            elif "12" in mva_code:
                outgoing_vat += amount * 0.12
            elif "0" in mva_code:
                outgoing_vat += 0
            else:
                outgoing_vat += amount * 0.25
        else:
            if "fradrag" in mva_code or mva_code in {"25", "15", "12"}:
                if "15" in mva_code:
                    incoming_vat += amount * 0.15
                elif "12" in mva_code:
                    incoming_vat += amount * 0.12
                else:
                    incoming_vat += amount * 0.25

    return {
        "incoming_vat": round(incoming_vat, 2),
        "outgoing_vat": round(outgoing_vat, 2),
        "estimated_settlement": round(outgoing_vat - incoming_vat, 2),
    }


@router.get("/reports/grants")
async def report_grants(farm_id: str = Query(...)) -> dict[str, Any]:
    """Grant and periodization oriented report."""
    rows = []
    for tx in _fetch_transactions(farm_id):
        account_code = tx.get("account_code", "")
        description = (tx.get("description") or "").lower()
        if account_code == "3100" or "tilskudd" in description:
            voucher_date = tx.get("voucher_date") or datetime.utcnow().date().isoformat()
            rows.append(
                {
                    "voucher_date": voucher_date,
                    "amount": float(tx.get("amount") or 0),
                    "description": tx.get("description") or "Tilskudd",
                    "period": _month_key(voucher_date),
                }
            )

    return {"rows": sorted(rows, key=lambda x: x["voucher_date"], reverse=True)}


@router.get("/reports/journal")
async def report_journal(farm_id: str = Query(...)) -> dict[str, Any]:
    """Voucher journal report."""
    vouchers = await list_vouchers(farm_id=farm_id)
    return {
        "rows": [
            {
                "voucher_id": v.id,
                "date": v.voucher_date,
                "file_name": v.file_name,
                "status": v.status,
                "account_code": v.account_code,
                "mva_code": v.mva_code,
                "amount": v.amount,
            }
            for v in vouchers
        ]
    }


@router.get("/reports/liquidity")
async def report_liquidity(farm_id: str = Query(...), opening_balance: float = Query(default=0.0)) -> dict[str, Any]:
    """Simple liquidity forecast based on booked transactions."""
    txs = _fetch_transactions(farm_id)
    txs_sorted = sorted(txs, key=lambda t: t.get("voucher_date", ""))

    balance = opening_balance
    points = []
    for tx in txs_sorted:
        amount = float(tx.get("amount") or 0)
        if tx.get("transaction_type") == "income":
            balance += amount
        else:
            balance -= amount

        points.append(
            {
                "date": tx.get("voucher_date"),
                "description": tx.get("description") or tx.get("category") or "Bilag",
                "balance": round(balance, 2),
            }
        )

    return {
        "opening_balance": opening_balance,
        "closing_balance": round(balance, 2),
        "points": points,
    }
