import os
from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient


os.environ.setdefault(
    "COSMOS_DB_CONNECTION_STRING",
    "not-used-in-unit-tests",
)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

from app.api.routes import accounting
from app.api.routes.accounting import _voucher_matches_filters


VOUCHER = {
    "id": "voucher-1",
    "farm_id": "farm-1",
    "file_name": "Felleskjopet-juli.pdf",
    "content_type": "application/pdf",
    "description": "Gjødsel til enga",
    "account_code": "4500",
    "mva_code": "25",
    "amount": 1250.0,
    "status": "ført",
    "voucher_date": "2026-07-15",
    "blob_url": "https://example.test/voucher-1.pdf",
    "ocr_suggested_supplier": "Felleskjøpet Agri",
    "ocr_text_preview": "KUNDEKVITTERING TRAKTORDEL",
}


class FakeDocumentsContainer:
    def __init__(self, items):
        self.items = items
        self.last_query = None
        self.last_parameters = None

    def query_items(self, *, query, parameters, enable_cross_partition_query):
        self.last_query = query
        self.last_parameters = parameters
        assert enable_cross_partition_query is True
        return self.items


def make_client(monkeypatch, items):
    container = FakeDocumentsContainer(items)
    monkeypatch.setattr(accounting, "get_documents_container", lambda: container)
    app = FastAPI()
    app.include_router(accounting.router)
    return TestClient(app), container


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


def test_voucher_endpoint_combines_filters_and_keeps_farm_scope(monkeypatch):
    other_voucher = {
        **VOUCHER,
        "id": "voucher-2",
        "description": "Diesel",
        "status": "mottatt",
        "voucher_date": "2026-08-01",
    }
    client, container = make_client(monkeypatch, [VOUCHER, other_voucher])

    response = client.get(
        "/vouchers",
        params={
            "farm_id": "farm-1",
            "q": "felleskjøpet",
            "status": "ført",
            "date_from": "2026-07-01",
            "date_to": "2026-07-31",
        },
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["voucher-1"]
    assert "c.farm_id = @farm_id" in container.last_query
    assert container.last_parameters == [{"name": "@farm_id", "value": "farm-1"}]


def test_voucher_endpoint_rejects_reversed_date_range(monkeypatch):
    client, _ = make_client(monkeypatch, [VOUCHER])

    response = client.get(
        "/vouchers",
        params={"farm_id": "farm-1", "date_from": "2026-08-01", "date_to": "2026-07-01"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Fra-dato kan ikke være etter til-dato"
