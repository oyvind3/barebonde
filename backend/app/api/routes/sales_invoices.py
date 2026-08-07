"""Farm-scoped sales invoice lifecycle: draft → issued → sent → paid.

Backend is authoritative for money: all amounts are integer øre, calculations
use Decimal with explicit rounding, and totals are always recomputed server-side.
"""

from __future__ import annotations

import base64
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from azure.cosmos import exceptions
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.api.dependencies.farm_access import AuthorizedFarm, require_farm_permission
from app.core.permissions import Permission
from app.db.cosmos_client import (
    get_bank_accounts_container,
    get_customers_container,
    get_farm_settings_container,
    get_sales_invoices_container,
)
from app.middleware.rate_limiter import rate_limit_dependency
from app.services.email_service import EmailDeliveryError, send_transactional_email, validate_plunk_configured
from app.services.sales_invoice_calculation import (
    SUPPORTED_VAT_RATES,
    calculate_invoice,
    format_nok,
)
from app.services.sales_invoice_pdf import build_invoice_pdf
from app.services.storage_service import StorageService

router = APIRouter()

IMMUTABLE_STATUSES = {"issued", "sent", "paid", "cancelled"}
UNIT_CHOICES = {"stk", "time", "kg", "liter", "daa", "oppdrag"}

_storage = StorageService()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _parse_iso_date(value: str, label: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} er ugyldig.")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class InvoiceLineInput(BaseModel):
    description: str = Field(default="", max_length=300)
    quantity: str = Field(default="1", max_length=20)
    unit: str = Field(default="stk", max_length=20)
    unit_price_ex_vat_ore: int = Field(ge=0)
    vat_rate: int


class InvoiceCreate(BaseModel):
    customer_id: str
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    reference: Optional[str] = Field(default="", max_length=140)
    message: Optional[str] = Field(default="", max_length=1000)
    lines: list[InvoiceLineInput] = Field(default_factory=list)


class InvoicePatch(BaseModel):
    customer_id: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    reference: Optional[str] = Field(default=None, max_length=140)
    message: Optional[str] = Field(default=None, max_length=1000)
    lines: Optional[list[InvoiceLineInput]] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_invoice(farm_id: str, invoice_id: str) -> dict:
    try:
        document = get_sales_invoices_container().read_item(item=invoice_id, partition_key=farm_id)
    except exceptions.CosmosResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fakturaen ble ikke funnet.") from exc
    if document.get("type") != "sales_invoice":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fakturaen ble ikke funnet.")
    return document


def _read_customer_document(farm_id: str, customer_id: str) -> dict:
    try:
        document = get_customers_container().read_item(item=customer_id, partition_key=farm_id)
    except exceptions.CosmosResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kunden ble ikke funnet.") from exc
    if document.get("type") != "customer":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kunden ble ikke funnet.")
    return document


def _read_settings(farm_id: str) -> Optional[dict]:
    try:
        return get_farm_settings_container().read_item(item=f"farm-settings:{farm_id}", partition_key=farm_id)
    except exceptions.CosmosResourceNotFoundError:
        return None


def _default_bank_account(farm_id: str) -> Optional[dict]:
    accounts = list(
        get_bank_accounts_container().query_items(
            query="SELECT * FROM c WHERE c.farm_id = @farm_id AND c.type = 'bank_account' AND c.status = 'active'",
            parameters=[{"name": "@farm_id", "value": farm_id}],
            partition_key=farm_id,
        )
    )
    for account in accounts:
        if account.get("is_default"):
            return account
    return accounts[0] if accounts else None


def _normalize_lines(raw_lines: list[InvoiceLineInput]) -> list[dict]:
    """Validate and normalize line inputs; computed amounts are added by calculate_invoice."""
    lines: list[dict] = []
    for index, line in enumerate(raw_lines, start=1):
        description = line.description.strip()
        if not description:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Linje {index} mangler beskrivelse.",
            )
        try:
            quantity = Decimal(line.quantity.strip().replace(",", "."))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Linje {index} har ugyldig antall.",
            )
        if quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Linje {index}: antall må være større enn 0.",
            )
        if line.vat_rate not in SUPPORTED_VAT_RATES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Linje {index}: MVA-satsen er ikke støttet.",
            )
        unit = line.unit.strip().lower() or "stk"
        lines.append(
            {
                "id": f"line:{uuid4()}",
                "description": description,
                "quantity": str(quantity.normalize()),
                "unit": unit if unit in UNIT_CHOICES else line.unit.strip()[:20],
                "unit_price_ex_vat_ore": int(line.unit_price_ex_vat_ore),
                "vat_rate": int(line.vat_rate),
            }
        )
    return lines


def _apply_lines_and_totals(document: dict, raw_lines: list[InvoiceLineInput]) -> None:
    lines = _normalize_lines(raw_lines)
    totals = calculate_invoice(lines)
    document["lines"] = totals["lines"]
    document["subtotal_ore"] = totals["subtotal_ore"]
    document["vat_total_ore"] = totals["vat_total_ore"]
    document["total_ore"] = totals["total_ore"]


def _invoice_response(document: dict) -> dict:
    return {
        "id": document["id"],
        "status": document.get("status") or "draft",
        "invoice_number": document.get("invoice_number"),
        "invoice_year": document.get("invoice_year"),
        "invoice_date": document.get("invoice_date"),
        "due_date": document.get("due_date"),
        "customer_id": document.get("customer_id"),
        "customer_snapshot": document.get("customer_snapshot") or {},
        "seller_snapshot": document.get("seller_snapshot"),
        "payment_account_snapshot": document.get("payment_account_snapshot"),
        "lines": document.get("lines") or [],
        "currency": document.get("currency") or "NOK",
        "subtotal_ore": int(document.get("subtotal_ore") or 0),
        "vat_total_ore": int(document.get("vat_total_ore") or 0),
        "total_ore": int(document.get("total_ore") or 0),
        "reference": document.get("reference") or "",
        "message": document.get("message") or "",
        "has_pdf": bool(document.get("pdf_blob_name")),
        "issued_at": document.get("issued_at"),
        "sent_at": document.get("sent_at"),
        "paid_at": document.get("paid_at"),
        "cancelled_at": document.get("cancelled_at"),
        "delivery": document.get("delivery")
        or {"recipient_email": None, "send_count": 0, "last_attempt_at": None, "last_success_at": None, "provider_message_id": None, "last_error": None},
        "version": document.get("version") or 1,
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
    }


def _validate_dates(document: dict) -> None:
    invoice_date = _parse_iso_date(document.get("invoice_date"), "Fakturadato")
    due_date = _parse_iso_date(document.get("due_date"), "Forfallsdato")
    if due_date < invoice_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forfallsdato kan ikke være før fakturadato.",
        )


def _next_invoice_number(farm_id: str, year: int) -> str:
    """Concurrency-safe per-farm invoice numbering using Cosmos ETag optimistic loop."""
    container = get_sales_invoices_container()
    sequence_id = f"sales-invoice-sequence:{farm_id}:{year}"

    for _ in range(5):
        try:
            sequence = container.read_item(item=sequence_id, partition_key=farm_id)
        except exceptions.CosmosResourceNotFoundError:
            sequence = {
                "id": sequence_id,
                "type": "sales_invoice_sequence",
                "farm_id": farm_id,
                "year": year,
                "last_number": 0,
                "created_at": now(),
                "updated_at": now(),
            }
            try:
                created = container.create_item(sequence)
                etag = created.get("_etag")
            except exceptions.CosmosResourceExistsError:
                continue
        else:
            etag = sequence.get("_etag")

        next_number = int(sequence.get("last_number") or 0) + 1
        sequence["last_number"] = next_number
        sequence["updated_at"] = now()
        try:
            container.replace_item(
                item=sequence_id,
                body=sequence,
                access_condition={"type": "IfMatch", "condition": etag},
            )
            return f"{year}-{next_number:04d}"
        except exceptions.CosmosAccessConditionFailedError:
            continue
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Kunne ikke tildele fakturanummer. Prøv igjen.",
    )


def _build_seller_snapshot(farm: dict, settings: dict) -> dict:
    return {
        "name": settings.get("legal_name") or farm.get("name") or "",
        "org_number": settings.get("org_number") or farm.get("org_number") or "",
        "address": settings.get("address_line_1") or "",
        "postal_code": settings.get("postal_code") or "",
        "city": settings.get("city") or "",
        "contact_email": settings.get("contact_email") or "",
        "contact_phone": settings.get("contact_phone") or "",
        "vat_registered": settings.get("vat_registered") or "unknown",
        "vat_number": settings.get("vat_number") or "",
    }


def _build_customer_snapshot(customer: dict) -> dict:
    return {
        "name": customer.get("name") or "",
        "org_number": customer.get("org_number") or "",
        "email": customer.get("email") or "",
        "address": customer.get("address") or "",
        "postal_code": customer.get("postal_code") or "",
        "city": customer.get("city") or "",
        "country_code": customer.get("country_code") or "NO",
    }


def _validate_issue(document: dict, farm: dict) -> tuple[dict, dict, dict]:
    """Validate everything required before issuing. Returns (settings, customer, bank_account)."""
    errors: list[str] = []

    settings = _read_settings(str(farm["id"])) or {}
    seller_name = settings.get("legal_name") or farm.get("name") or ""
    if not seller_name:
        errors.append("Gården mangler juridisk navn (se Innstillinger).")
    if not (settings.get("org_number") or farm.get("org_number")):
        errors.append("Gården mangler organisasjonsnummer (se Innstillinger).")
    if not settings.get("address_line_1"):
        errors.append("Gården mangler adresse (se Innstillinger).")
    if not settings.get("postal_code"):
        errors.append("Gården mangler postnummer (se Innstillinger).")
    if not settings.get("city"):
        errors.append("Gården mangler sted (se Innstillinger).")

    bank_account = _default_bank_account(str(farm["id"]))
    if not bank_account:
        errors.append("Gården mangler standard bankkonto (se Innstillinger → Bankkontoer).")

    try:
        _validate_dates(document)
    except HTTPException as exc:
        errors.append(str(exc.detail))

    if not document.get("customer_id"):
        errors.append("Fakturaen mangler kunde.")
    customer = None
    if document.get("customer_id"):
        try:
            customer = _read_customer_document(str(farm["id"]), document["customer_id"])
        except HTTPException:
            errors.append("Kunden finnes ikke lenger.")

    if not document.get("lines"):
        errors.append("Fakturaen mangler fakturalinjer.")

    if int(document.get("total_ore") or 0) <= 0:
        errors.append("Fakturatotalen må være større enn 0.")

    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=errors)

    return settings, customer, bank_account


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.get("/farms/{farm_id}/sales-invoices")
def list_sales_invoices(
    access: AuthorizedFarm = Depends(require_farm_permission(Permission.SALES_INVOICE_READ)),
) -> dict:
    farm_id = str(access.farm["id"])
    items = list(
        get_sales_invoices_container().query_items(
            query="SELECT * FROM c WHERE c.farm_id = @farm_id AND c.type = 'sales_invoice'",
            parameters=[{"name": "@farm_id", "value": farm_id}],
            partition_key=farm_id,
        )
    )
    items.sort(key=lambda item: (item.get("created_at") or ""), reverse=True)
    return {"invoices": [_invoice_response(item) for item in items]}


@router.post("/farms/{farm_id}/sales-invoices", status_code=status.HTTP_201_CREATED)
def create_sales_invoice(
    request: InvoiceCreate,
    access: AuthorizedFarm = Depends(require_farm_permission(Permission.SALES_INVOICE_CREATE, require_csrf_protection=True)),
) -> dict:
    farm_id = str(access.farm["id"])
    customer = _read_customer_document(farm_id, request.customer_id)

    settings = _read_settings(farm_id) or {}
    invoice_date = date.today()
    if request.invoice_date:
        invoice_date = _parse_iso_date(request.invoice_date, "Fakturadato")
    payment_terms = int(settings.get("payment_terms_days") or 14)
    due_date = invoice_date + timedelta(days=payment_terms)
    if request.due_date:
        due_date = _parse_iso_date(request.due_date, "Forfallsdato")
    if due_date < invoice_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forfallsdato kan ikke være før fakturadato.",
        )

    invoice_id = f"sales-invoice:{farm_id}:{uuid4()}"
    document = {
        "id": invoice_id,
        "type": "sales_invoice",
        "farm_id": farm_id,
        "status": "draft",
        "invoice_number": None,
        "invoice_year": None,
        "invoice_date": invoice_date.isoformat(),
        "due_date": due_date.isoformat(),
        "customer_id": customer["id"],
        "customer_snapshot": {},
        "seller_snapshot": None,
        "lines": [],
        "currency": "NOK",
        "subtotal_ore": 0,
        "vat_total_ore": 0,
        "total_ore": 0,
        "payment_account_snapshot": None,
        "reference": (request.reference or "").strip(),
        "message": (request.message or "").strip(),
        "pdf_blob_name": None,
        "pdf_generated_at": None,
        "issued_at": None,
        "sent_at": None,
        "paid_at": None,
        "cancelled_at": None,
        "delivery": {
            "recipient_email": None,
            "send_count": 0,
            "last_attempt_at": None,
            "last_success_at": None,
            "provider_message_id": None,
            "last_error": None,
        },
        "created_by_user_id": access.current.user["user_id"],
        "updated_by_user_id": access.current.user["user_id"],
        "version": 1,
        "created_at": now(),
        "updated_at": now(),
    }
    _apply_lines_and_totals(document, request.lines)

    try:
        get_sales_invoices_container().create_item(document)
    except exceptions.CosmosHttpResponseError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="sales_invoices_unavailable",
        ) from exc
    return _invoice_response(document)


@router.get("/farms/{farm_id}/sales-invoices/{invoice_id}")
def get_sales_invoice(
    invoice_id: str,
    access: AuthorizedFarm = Depends(require_farm_permission(Permission.SALES_INVOICE_READ)),
) -> dict:
    document = _read_invoice(str(access.farm["id"]), invoice_id)
    return _invoice_response(document)


@router.patch("/farms/{farm_id}/sales-invoices/{invoice_id}")
def patch_sales_invoice(
    invoice_id: str,
    request: InvoicePatch,
    access: AuthorizedFarm = Depends(require_farm_permission(Permission.SALES_INVOICE_UPDATE, require_csrf_protection=True)),
) -> dict:
    farm_id = str(access.farm["id"])
    container = get_sales_invoices_container()
    document = _read_invoice(farm_id, invoice_id)

    if document.get("status") != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fakturaen er allerede utstedt og kan ikke redigeres.",
        )

    updates = request.model_dump(exclude_unset=True)

    if "customer_id" in updates and updates["customer_id"]:
        _read_customer_document(farm_id, updates["customer_id"])
        document["customer_id"] = updates["customer_id"]

    if "invoice_date" in updates and updates["invoice_date"]:
        document["invoice_date"] = _parse_iso_date(updates["invoice_date"], "Fakturadato").isoformat()

    if "due_date" in updates and updates["due_date"]:
        document["due_date"] = _parse_iso_date(updates["due_date"], "Forfallsdato").isoformat()

    _validate_dates(document)

    if "reference" in updates:
        document["reference"] = (updates.get("reference") or "").strip()

    if "message" in updates:
        document["message"] = (updates.get("message") or "").strip()

    if "lines" in updates and updates["lines"] is not None:
        _apply_lines_and_totals(document, [InvoiceLineInput(**line) for line in updates["lines"]])

    document["updated_by_user_id"] = access.current.user["user_id"]
    document["version"] = int(document.get("version") or 1) + 1
    document["updated_at"] = now()
    container.upsert_item(document)
    return _invoice_response(document)


@router.post("/farms/{farm_id}/sales-invoices/{invoice_id}/cancel")
def cancel_sales_invoice(
    invoice_id: str,
    access: AuthorizedFarm = Depends(require_farm_permission(Permission.SALES_INVOICE_UPDATE, require_csrf_protection=True)),
) -> dict:
    farm_id = str(access.farm["id"])
    container = get_sales_invoices_container()
    document = _read_invoice(farm_id, invoice_id)
    if document.get("status") != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kun utkast kan kanselleres.",
        )
    document["status"] = "cancelled"
    document["cancelled_at"] = now()
    document["updated_by_user_id"] = access.current.user["user_id"]
    document["version"] = int(document.get("version") or 1) + 1
    document["updated_at"] = now()
    container.upsert_item(document)
    return _invoice_response(document)


# ---------------------------------------------------------------------------
# Issue
# ---------------------------------------------------------------------------


@router.post("/farms/{farm_id}/sales-invoices/{invoice_id}/issue")
def issue_sales_invoice(
    invoice_id: str,
    access: AuthorizedFarm = Depends(require_farm_permission(Permission.SALES_INVOICE_ISSUE, require_csrf_protection=True)),
    _: None = Depends(rate_limit_dependency("invoice_issue")),
) -> dict:
    farm_id = str(access.farm["id"])
    container = get_sales_invoices_container()
    document = _read_invoice(farm_id, invoice_id)

    if document.get("status") != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fakturaen er allerede utstedt og kan ikke utstedes på nytt.",
        )

    settings, customer, bank_account = _validate_issue(document, access.farm)

    # Recompute totals server-side from persisted lines (never trust stored totals).
    totals = calculate_invoice(document.get("lines") or [])
    document["lines"] = totals["lines"]
    document["subtotal_ore"] = totals["subtotal_ore"]
    document["vat_total_ore"] = totals["vat_total_ore"]
    document["total_ore"] = totals["total_ore"]

    invoice_year = _parse_iso_date(document["invoice_date"], "Fakturadato").year
    invoice_number = _next_invoice_number(farm_id, invoice_year)

    document["invoice_number"] = invoice_number
    document["invoice_year"] = invoice_year
    document["seller_snapshot"] = _build_seller_snapshot(access.farm, settings)
    document["customer_snapshot"] = _build_customer_snapshot(customer)
    document["payment_account_snapshot"] = {
        "account_id": bank_account["id"],
        "display_name": bank_account.get("display_name") or "",
        "account_number": str(bank_account.get("account_number") or ""),
    }

    # Generate the permanent PDF before persisting issued state.
    document["status"] = "issued"
    pdf_bytes = build_invoice_pdf(document, draft=False)
    try:
        upload = _storage.upload_file(
            farm_id=farm_id,
            document_id=invoice_id,
            file_name=f"faktura-{invoice_number}.pdf",
            content_type="application/pdf",
            payload=pdf_bytes,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Kunne ikke lagre faktura-PDF. Prøv igjen.",
        )

    document["pdf_blob_name"] = upload["blob_name"]
    document["pdf_generated_at"] = now()
    document["issued_at"] = now()
    document["updated_by_user_id"] = access.current.user["user_id"]
    document["version"] = int(document.get("version") or 1) + 1
    document["updated_at"] = now()
    container.upsert_item(document)
    return _invoice_response(document)


# ---------------------------------------------------------------------------
# PDF preview / download
# ---------------------------------------------------------------------------


@router.post("/farms/{farm_id}/sales-invoices/{invoice_id}/preview")
def preview_sales_invoice_pdf(
    invoice_id: str,
    access: AuthorizedFarm = Depends(require_farm_permission(Permission.SALES_INVOICE_READ)),
) -> Response:
    farm_id = str(access.farm["id"])
    document = _read_invoice(farm_id, invoice_id)

    if document.get("status") != "draft":
        # For issued+ invoices the permanent PDF is served via /pdf.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fakturaen er utstedt. Bruk PDF-nedlasting i stedet.",
        )

    # Preview uses backend-authoritative data; enrich with live seller/payment
    # context so the user sees a realistic document without persisting anything.
    settings = _read_settings(farm_id) or {}
    preview_document = dict(document)
    preview_document["seller_snapshot"] = _build_seller_snapshot(access.farm, settings)
    if not preview_document.get("customer_snapshot"):
        try:
            customer = _read_customer_document(farm_id, document["customer_id"])
            preview_document["customer_snapshot"] = _build_customer_snapshot(customer)
        except HTTPException:
            preview_document["customer_snapshot"] = {}
    bank_account = _default_bank_account(farm_id)
    preview_document["payment_account_snapshot"] = (
        {
            "account_id": bank_account["id"],
            "display_name": bank_account.get("display_name") or "",
            "account_number": str(bank_account.get("account_number") or ""),
        }
        if bank_account
        else {}
    )

    pdf_bytes = build_invoice_pdf(preview_document, draft=True)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "inline; filename=utkast.pdf"})


@router.get("/farms/{farm_id}/sales-invoices/{invoice_id}/pdf")
def download_sales_invoice_pdf(
    invoice_id: str,
    access: AuthorizedFarm = Depends(require_farm_permission(Permission.SALES_INVOICE_READ)),
) -> Response:
    document = _read_invoice(str(access.farm["id"]), invoice_id)
    blob_name = document.get("pdf_blob_name")
    if not blob_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fakturaen har ingen PDF ennå.",
        )
    try:
        payload = _storage.download_file(blob_name)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Kunne ikke hente faktura-PDF. Prøv igjen.",
        )
    filename = f"faktura-{document.get('invoice_number') or 'utkast'}.pdf"
    return Response(
        content=payload,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Send / resend
# ---------------------------------------------------------------------------


def _compose_email(document: dict) -> tuple[str, str]:
    seller = document.get("seller_snapshot") or {}
    seller_name = seller.get("name") or "selger"
    number = document.get("invoice_number") or ""
    total = format_nok(int(document.get("total_ore") or 0))
    due = document.get("due_date") or ""
    if len(due) == 10:
        due = f"{due[8:10]}.{due[5:7]}.{due[0:4]}"
    subject = f"Faktura {number} fra {seller_name}"
    body = (
        f"<p>Hei,</p>"
        f"<p>Vedlagt finner du faktura {number} fra {seller_name}.</p>"
        f"<p>Beløp: {total} kr<br/>Forfall: {due}</p>"
        f"<p>Vennlig hilsen<br/>{seller_name}</p>"
    )
    return subject, body


async def _deliver_invoice(farm_id: str, document: dict, container) -> dict:
    delivery = dict(document.get("delivery") or {})
    recipient = (document.get("customer_snapshot") or {}).get("email") or ""
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kunden mangler e-postadresse.",
        )

    validate_plunk_configured()

    attempt = int(delivery.get("send_count") or 0) + 1
    idempotency_key = f"sales-invoice:{document['id']}:send:{attempt}"

    try:
        payload = _storage.download_file(document["pdf_blob_name"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Kunne ikke hente faktura-PDF. Prøv igjen.",
        )

    subject, body = _compose_email(document)
    attachments = [
        {
            "name": f"faktura-{document.get('invoice_number') or 'utkast'}.pdf",
            "content": base64.b64encode(payload).decode("ascii"),
        }
    ]

    delivery["recipient_email"] = recipient
    delivery["last_attempt_at"] = now()

    try:
        result = await send_transactional_email(
            to=recipient,
            subject=subject,
            body=body,
            attachments=attachments,
            idempotency_key=idempotency_key,
        )
    except EmailDeliveryError:
        delivery["last_error"] = "E-posten kunne ikke sendes."
        document["delivery"] = delivery
        document["updated_at"] = now()
        container.upsert_item(document)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Fakturaen er utstedt, men e-posten kunne ikke sendes. Du kan prøve igjen.",
        )

    delivery["send_count"] = attempt
    delivery["last_success_at"] = now()
    delivery["last_error"] = None
    message_id = None
    if isinstance(result, dict):
        data = result.get("data")
        if isinstance(data, dict):
            message_id = data.get("id")
        message_id = message_id or result.get("id")
    delivery["provider_message_id"] = message_id

    document["delivery"] = delivery
    if document.get("status") == "issued":
        document["status"] = "sent"
        document["sent_at"] = now()
    document["version"] = int(document.get("version") or 1) + 1
    document["updated_at"] = now()
    container.upsert_item(document)
    return document


@router.post("/farms/{farm_id}/sales-invoices/{invoice_id}/send")
async def send_sales_invoice(
    invoice_id: str,
    access: AuthorizedFarm = Depends(require_farm_permission(Permission.SALES_INVOICE_SEND, require_csrf_protection=True)),
    _: None = Depends(rate_limit_dependency("invoice_send")),
) -> dict:
    farm_id = str(access.farm["id"])
    container = get_sales_invoices_container()
    document = _read_invoice(farm_id, invoice_id)
    if document.get("status") not in {"issued", "sent"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fakturaen må være utstedt før den kan sendes.",
        )
    if document.get("status") == "sent":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fakturaen er allerede sendt. Bruk «Send på nytt».",
        )
    document = await _deliver_invoice(farm_id, document, container)
    return _invoice_response(document)


@router.post("/farms/{farm_id}/sales-invoices/{invoice_id}/resend")
async def resend_sales_invoice(
    invoice_id: str,
    access: AuthorizedFarm = Depends(require_farm_permission(Permission.SALES_INVOICE_SEND, require_csrf_protection=True)),
    _: None = Depends(rate_limit_dependency("invoice_send")),
) -> dict:
    farm_id = str(access.farm["id"])
    container = get_sales_invoices_container()
    document = _read_invoice(farm_id, invoice_id)
    if document.get("status") not in {"issued", "sent"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fakturaen må være utstedt før den kan sendes.",
        )
    document = await _deliver_invoice(farm_id, document, container)
    return _invoice_response(document)


# ---------------------------------------------------------------------------
# Mark paid
# ---------------------------------------------------------------------------


@router.post("/farms/{farm_id}/sales-invoices/{invoice_id}/mark-paid")
def mark_sales_invoice_paid(
    invoice_id: str,
    access: AuthorizedFarm = Depends(require_farm_permission(Permission.SALES_INVOICE_MARK_PAID, require_csrf_protection=True)),
) -> dict:
    farm_id = str(access.farm["id"])
    container = get_sales_invoices_container()
    document = _read_invoice(farm_id, invoice_id)
    if document.get("status") not in {"issued", "sent"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kun utstedte eller sendte fakturaer kan markeres som betalt.",
        )
    document["status"] = "paid"
    document["paid_at"] = now()
    document["updated_by_user_id"] = access.current.user["user_id"]
    document["version"] = int(document.get("version") or 1) + 1
    document["updated_at"] = now()
    container.upsert_item(document)
    return _invoice_response(document)