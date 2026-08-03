import os
from datetime import date


os.environ.setdefault(
    "COSMOS_DB_CONNECTION_STRING",
    "AccountEndpoint=https://localhost:8081/;AccountKey=test;",
)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

from app.api.routes.accounting import _voucher_matches_filters


VOUCHER = {
    "file_name": "Felleskjopet-juli.pdf",
    "description": "Gjødsel til enga",
    "account_code": "4500",
    "status": "ført",
    "voucher_date": "2026-07-15",
    "ocr_suggested_supplier": "Felleskjøpet Agri",
    "ocr_text_preview": "KUNDEKVITTERING TRAKTORDEL",
}


def test_search_is_case_insensitive_across_document_fields():
    assert _voucher_matches_filters(VOUCHER, q="FELLESKJØPET")
    assert _voucher_matches_filters(VOUCHER, q="traktordel")
    assert _voucher_matches_filters(VOUCHER, q="4500")
    assert not _voucher_matches_filters(VOUCHER, q="diesel")


def test_status_and_date_filters_can_be_combined():
    assert _voucher_matches_filters(
        VOUCHER,
        voucher_status="FØRT",
        date_from=date(2026, 7, 1),
        date_to=date(2026, 7, 31),
    )
    assert not _voucher_matches_filters(VOUCHER, voucher_status="mottatt")
    assert not _voucher_matches_filters(VOUCHER, date_from=date(2026, 7, 16))
    assert not _voucher_matches_filters(VOUCHER, date_to=date(2026, 7, 14))


def test_empty_filters_preserve_existing_list_behavior():
    assert _voucher_matches_filters(VOUCHER)
