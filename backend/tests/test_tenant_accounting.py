import os
from types import SimpleNamespace

from azure.cosmos import exceptions
from fastapi import FastAPI
from fastapi.testclient import TestClient


os.environ.setdefault("COSMOS_DB_CONNECTION_STRING", "not-used-in-unit-tests")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("IDENTITY_HMAC_KEY", "test-identity-hmac-key")

from app.api.dependencies import farm_access, identity as identity_dependency
from app.api.routes import accounting
from app.core.permissions import permissions_for_role
from app.services import journal_service
from app.services.membership_service import InactiveMembershipError, MembershipNotFoundError
from app.services.ocr_service import OCRResult
from app.services.storage_service import StorageService


class MemoryContainer:
    def __init__(self, items=None):
        self.items = {item["id"]: dict(item) for item in (items or [])}
        self.last_query = ""
        self.last_parameters = []
        self.last_partition_key = None
        self.fail_create = False
        self.fail_upsert = False

    def read_item(self, *, item, partition_key):
        document = self.items.get(item)
        if document is None or document.get("farm_id") != partition_key:
            raise exceptions.CosmosResourceNotFoundError(message="missing", response=None)
        return dict(document)

    def query_items(self, *, query, parameters, partition_key):
        self.last_query = query
        self.last_parameters = list(parameters)
        self.last_partition_key = partition_key
        values = {parameter["name"]: parameter["value"] for parameter in parameters}
        assert values["@farm_id"] == partition_key
        expected_type = "voucher_document" if "voucher_document" in query else "accounting_transaction"
        return [
            dict(item)
            for item in self.items.values()
            if item.get("farm_id") == partition_key and item.get("type") == expected_type
        ]

    def create_item(self, item):
        if self.fail_create:
            raise RuntimeError("cosmos unavailable")
        if item["id"] in self.items:
            raise exceptions.CosmosResourceExistsError(message="exists", response=None)
        self.items[item["id"]] = dict(item)
        return dict(item)

    def upsert_item(self, item):
        if self.fail_upsert:
            raise RuntimeError("cosmos unavailable")
        self.items[item["id"]] = dict(item)
        return dict(item)

    def delete_item(self, *, item, partition_key):
        document = self.items.get(item)
        if document is None or document.get("farm_id") != partition_key:
            raise exceptions.CosmosResourceNotFoundError(message="missing", response=None)
        del self.items[item]


class FakeStorage:
    def __init__(self):
        self.uploads = []
        self.deleted = []
        self.payloads = {}
        self.fail_upload = False
        self.fail_download = False

    def upload_file(self, *, farm_id, document_id, file_name, content_type, payload):
        if self.fail_upload:
            raise RuntimeError("storage unavailable")
        blob_name = f"{farm_id}/{document_id}/document.pdf"
        self.uploads.append({"farm_id": farm_id, "document_id": document_id, "file_name": file_name, "blob_name": blob_name})
        self.payloads[blob_name] = payload
        return {"blob_name": blob_name, "content_type": content_type, "size_bytes": len(payload)}

    def download_file(self, blob_name):
        if self.fail_download:
            raise RuntimeError("storage unavailable")
        return self.payloads[blob_name]

    def delete_file(self, blob_name):
        self.deleted.append(blob_name)
        self.payloads.pop(blob_name, None)


def voucher(voucher_id="voucher-a", farm_id="farm-a", **overrides):
    document = {
        "id": voucher_id,
        "type": "voucher_document",
        "farm_id": farm_id,
        "file_name": "bilag.pdf",
        "content_type": "application/pdf",
        "size_bytes": 4,
        "blob_name": f"{farm_id}/{voucher_id}/document.pdf",
        "blob_url": "https://legacy.example.invalid/never-use-this",
        "status": "mottatt",
        "amount": 100.0,
        "account_code": None,
        "mva_code": None,
        "voucher_date": "2026-08-01",
        "description": "Diesel",
        "created_by_user_id": "user-a",
        "created_at": "2026-08-01T00:00:00+00:00",
    }
    document.update(overrides)
    return document


def transaction(transaction_id="transaction-a", farm_id="farm-a", **overrides):
    item = {
        "id": transaction_id,
        "type": "accounting_transaction",
        "farm_id": farm_id,
        "voucher_id": "voucher-a",
        "transaction_type": "expense",
        "category": "Drift",
        "amount": 100.0,
        "account_code": "4500",
        "voucher_date": "2026-08-01",
        "description": "Diesel",
        "created_by_user_id": "user-a",
        "created_at": "2026-08-01T00:00:00+00:00",
    }
    item.update(overrides)
    return item


def make_client(monkeypatch, *, role="owner", documents=None, transactions=None, memberships=None):
    state = SimpleNamespace(
        documents=MemoryContainer(documents),
        transactions=MemoryContainer(transactions),
        audits=MemoryContainer(),
        storage=FakeStorage(),
        farms={"farm-a": {"id": "farm-a", "farm_status": "active"}, "farm-b": {"id": "farm-b", "farm_status": "active"}},
        memberships=memberships or {"farm-a": {"user_id": "user-a", "farm_role": role, "membership_status": "active"}},
    )

    class FakeSessionService:
        def get_session(self, raw_token):
            assert raw_token == "session-cookie"
            return (
                {"id": "session-1", "expires_at": "2027-01-01T00:00:00+00:00"},
                {"user_id": "user-a", "email": "ola@example.com", "status": "active"},
            )

        def csrf_token(self, _raw_token):
            return "csrf-token"

    class FakeMembershipService:
        def get_active_membership(self, *, farm_id, user_id):
            membership = state.memberships.get(farm_id)
            if membership is None or membership.get("user_id") != user_id:
                raise MembershipNotFoundError()
            if membership.get("membership_status") != "active" or not membership.get("farm_role"):
                raise InactiveMembershipError()
            return dict(membership)

        def get_farm(self, farm_id):
            return state.farms.get(farm_id)

        def permissions_for_membership(self, membership):
            return permissions_for_role(membership.get("farm_role"))

    monkeypatch.setattr(identity_dependency, "SessionService", FakeSessionService)
    monkeypatch.setattr(farm_access, "MembershipService", FakeMembershipService)
    monkeypatch.setattr(accounting, "get_documents_container", lambda: state.documents)
    monkeypatch.setattr(accounting, "get_transactions_container", lambda: state.transactions)
    monkeypatch.setattr(accounting, "get_audit_logs_container", lambda: state.audits)
    monkeypatch.setattr(accounting, "storage_service", state.storage)
    
    journal_container = MemoryContainer()
    monkeypatch.setattr("app.db.cosmos_client.get_journal_entries_container", lambda: journal_container)
    
    def mock_post_entry(**kwargs):
        entry = {
            "id": f"journal-entry:{kwargs.get('source_key', 'test')}",
            "type": "journal_entry",
            "farm_id": kwargs["farm_id"],
            "journal_number": 1,
            "posting_date": kwargs.get("posting_date", "2026-08-01"),
            "lines": kwargs.get("lines", []),
        }
        journal_container.create_item(entry)
        return entry
    
    def mock_list_entries(farm_id, **kwargs):
        return [
            item for item in journal_container.items.values()
            if item.get("farm_id") == farm_id and item.get("type") == "journal_entry"
        ]
    
    monkeypatch.setattr(accounting.journal_service, "post_entry", mock_post_entry)
    monkeypatch.setattr(accounting.journal_service, "list_entries", mock_list_entries)
    monkeypatch.setattr(accounting.ocr_service, "extract_text", lambda **_: OCRResult("Diesel 100,00", "fake-ocr", 0.9, []))
    monkeypatch.setattr(
        accounting.ocr_service,
        "infer_fields",
        lambda _text: {"suggested_amount": 100.0, "suggested_date": "2026-08-01", "suggested_supplier": "Leverandør", "text_preview": "Diesel 100,00"},
    )

    app = FastAPI()
    app.include_router(accounting.router)
    return TestClient(app), state


def authenticated_headers():
    return {"X-CSRF-Token": "csrf-token"}


def authenticated_upload(client, path, *, data=None):
    return client.post(
        path,
        files={"file": ("bilag.pdf", b"PDF!", "application/pdf")},
        data=data or {},
        cookies={"barebonde_session": "session-cookie"},
        headers=authenticated_headers(),
    )


def test_blob_filename_discards_client_path_and_name_data():
    assert StorageService._safe_blob_filename("../../Ola Nordmann-private.pdf") == "document.pdf"
    assert StorageService._safe_blob_filename(r"C:\\uploads\\bilag.PNG") == "document.png"


def test_voucher_routes_require_a_session_and_csrf(monkeypatch):
    client, _ = make_client(monkeypatch)

    assert client.get("/api/farms/farm-a/vouchers").status_code == 401
    response = client.post(
        "/api/farms/farm-a/vouchers",
        files={"file": ("bilag.pdf", b"PDF!", "application/pdf")},
        cookies={"barebonde_session": "session-cookie"},
    )
    assert response.status_code == 403


def test_upload_uses_path_farm_and_server_principal_and_never_returns_blob_url(monkeypatch):
    client, state = make_client(monkeypatch)

    response = authenticated_upload(client, "/api/farms/farm-a/vouchers", data={"description": "Diesel"})

    assert response.status_code == 201
    payload = response.json()
    assert payload["farm_id"] == "farm-a"
    assert "blob_url" not in payload
    stored = state.documents.items[payload["id"]]
    assert stored["farm_id"] == "farm-a"
    assert stored["created_by_user_id"] == "user-a"
    assert state.storage.uploads[0]["blob_name"].startswith(f"farm-a/{payload['id']}/")
    assert state.documents.last_partition_key is None


def test_upload_rejects_conflicting_form_farm_id_without_writing_a_blob(monkeypatch):
    client, state = make_client(monkeypatch)

    response = authenticated_upload(client, "/api/farms/farm-a/vouchers", data={"farm_id": "farm-b"})

    assert response.status_code == 400
    assert state.storage.uploads == []
    assert state.documents.items == {}


def test_upload_cleans_up_blob_when_metadata_write_fails(monkeypatch):
    client, state = make_client(monkeypatch)
    state.documents.fail_create = True

    response = authenticated_upload(client, "/api/farms/farm-a/vouchers")

    assert response.status_code == 503
    assert state.storage.deleted == [state.storage.uploads[0]["blob_name"]]
    assert "cosmos unavailable" not in response.text


def test_upload_hides_storage_failure_details(monkeypatch):
    client, state = make_client(monkeypatch)
    state.storage.fail_upload = True

    response = authenticated_upload(client, "/api/farms/farm-a/vouchers")

    assert response.status_code == 503
    assert "storage unavailable" not in response.text


def test_staff_can_upload_a_draft_but_cannot_book_it(monkeypatch):
    client, _ = make_client(monkeypatch, role="staff")

    uploaded = authenticated_upload(client, "/api/farms/farm-a/vouchers")
    assert uploaded.status_code == 201
    booked = client.post(
        f"/api/farms/farm-a/vouchers/{uploaded.json()['id']}/book",
        json={"amount": 100, "account_code": "4500"},
        cookies={"barebonde_session": "session-cookie"},
        headers=authenticated_headers(),
    )
    assert booked.status_code == 403


def test_manager_can_book_a_voucher(monkeypatch):
    client, _ = make_client(monkeypatch, role="manager", documents=[voucher()])

    response = client.post(
        "/api/farms/farm-a/vouchers/voucher-a/book",
        json={"amount": 100, "account_code": "4500"},
        cookies={"barebonde_session": "session-cookie"},
        headers=authenticated_headers(),
    )

    assert response.status_code == 200


def test_cross_tenant_documents_vouchers_booking_and_reports_are_hidden(monkeypatch):
    client, state = make_client(
        monkeypatch,
        documents=[voucher("voucher-a", "farm-a"), voucher("voucher-b", "farm-b")],
        transactions=[transaction("transaction-a", "farm-a"), transaction("transaction-b", "farm-b", amount=900)],
    )
    state.storage.payloads["farm-a/voucher-a/document.pdf"] = b"farm a"
    state.storage.payloads["farm-b/voucher-b/document.pdf"] = b"farm b"

    assert client.get("/api/farms/farm-b/vouchers", cookies={"barebonde_session": "session-cookie"}).status_code == 404
    assert client.get("/api/farms/farm-a/documents/voucher-b", cookies={"barebonde_session": "session-cookie"}).status_code == 404
    assert client.get("/api/farms/farm-a/documents/voucher-b/download", cookies={"barebonde_session": "session-cookie"}).status_code == 404
    assert client.post(
        "/api/farms/farm-b/vouchers/voucher-b/book",
        json={"amount": 900, "account_code": "4500"},
        cookies={"barebonde_session": "session-cookie"},
        headers=authenticated_headers(),
    ).status_code == 404
    assert client.get("/api/farms/farm-b/reports/monthly", cookies={"barebonde_session": "session-cookie"}).status_code == 404

    report = client.get("/api/farms/farm-a/reports/monthly", cookies={"barebonde_session": "session-cookie"})
    assert report.status_code == 200
    assert report.json()["rows"][0]["expense"] == 100
    assert state.transactions.last_partition_key == "farm-a"
    assert "enable_cross_partition_query" not in state.transactions.last_query


def test_document_read_and_download_are_authorized_and_stream_private_blob(monkeypatch):
    client, state = make_client(monkeypatch, documents=[voucher()])
    state.storage.payloads["farm-a/voucher-a/document.pdf"] = b"private-pdf"

    metadata = client.get("/api/farms/farm-a/documents/voucher-a", cookies={"barebonde_session": "session-cookie"})
    assert metadata.status_code == 200
    assert "blob_url" not in metadata.json()

    download = client.get("/api/farms/farm-a/documents/voucher-a/download", cookies={"barebonde_session": "session-cookie"})
    assert download.status_code == 200
    assert download.content == b"private-pdf"
    assert download.headers["content-type"].startswith("application/pdf")
    assert download.headers["content-disposition"].startswith("attachment;")
    assert download.headers["x-content-type-options"] == "nosniff"


def test_booking_is_partition_scoped_creates_one_transaction_and_rejects_retry(monkeypatch):
    client, state = make_client(monkeypatch, documents=[voucher()])

    first = client.post(
        "/api/farms/farm-a/vouchers/voucher-a/book",
        json={"amount": 200, "account_code": "4500", "mva_code": "25", "transaction_type": "expense"},
        cookies={"barebonde_session": "session-cookie"},
        headers=authenticated_headers(),
    )
    second = client.post(
        "/api/farms/farm-a/vouchers/voucher-a/book",
        json={"amount": 200, "account_code": "4500"},
        cookies={"barebonde_session": "session-cookie"},
        headers=authenticated_headers(),
    )

    assert first.status_code == 200
    assert first.json()["status"] == "ført"
    assert second.status_code == 409
    created = state.transactions.items["transaction:voucher-a"]
    assert created["farm_id"] == "farm-a"
    assert created["created_by_user_id"] == "user-a"


def test_voucher_listing_uses_the_farm_partition_and_applies_filters(monkeypatch):
    client, state = make_client(
        monkeypatch,
        documents=[voucher("voucher-a", "farm-a", description="Diesel", status="ført"), voucher("voucher-b", "farm-b", description="Diesel")],
    )

    response = client.get(
        "/api/farms/farm-a/vouchers",
        params={"q": "diesel", "status": "ført", "date_from": "2026-08-01", "date_to": "2026-08-01"},
        cookies={"barebonde_session": "session-cookie"},
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["voucher-a"]
    assert state.documents.last_partition_key == "farm-a"
    assert "c.farm_id = @farm_id" in state.documents.last_query
