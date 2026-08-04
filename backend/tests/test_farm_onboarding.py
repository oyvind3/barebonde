import os

from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("COSMOS_DB_CONNECTION_STRING", "not-used-in-unit-tests")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

from app.api.routes import farms
from app.db.cosmos_models import Farm


def make_client() -> TestClient:
    app = FastAPI()
    app.include_router(farms.router, prefix="/api/farms")
    return TestClient(app)


def test_farm_model_round_trips_onboarding_profile():
    farm = Farm(
        name="Solberg gård",
        org_number="123456789",
        organization_form="ENK",
        industry_code="Dyrking av korn",
        primary_farm_type="plante",
        production_types=["korn", "grovfor"],
        farm_size_range="50_199",
        team_size="2_5",
        onboarding_goals=["regnskap", "frister"],
        billing_method="faktura",
        billing_email="faktura@solberg.no",
    )

    restored = Farm.from_dict(farm.to_dict())

    assert restored.production_types == ["korn", "grovfor"]
    assert restored.onboarding_goals == ["regnskap", "frister"]
    assert restored.billing_email == "faktura@solberg.no"


def test_create_farm_persists_targeted_onboarding_profile(monkeypatch):
    saved_farms = []
    saved_links = []
    queries = []

    class FarmsContainer:
        def query_items(self, **kwargs):
            queries.append(kwargs)
            return []

        def upsert_item(self, item):
            saved_farms.append(item)

    class FarmUsersContainer:
        def upsert_item(self, item):
            saved_links.append(item)

    async def lookup_org(_org_number):
        return {
            "name": "Solberg gård",
            "address": "Gårdsveien 14",
            "municipality": "Nes",
            "organization_form": "ENK",
            "industry_code": "Dyrking av korn",
        }

    monkeypatch.setattr(farms, "get_farms_container", lambda: FarmsContainer())
    monkeypatch.setattr(farms, "get_farm_users_container", lambda: FarmUsersContainer())
    monkeypatch.setattr(farms.brreg_service, "lookup_org", lookup_org)

    response = make_client().post(
        "/api/farms",
        headers={"X-Onboarding-User-Id": "user-123"},
        json={
            "name": "Solberg gård",
            "org_number": "123456789",
            "primary_farm_type": "plante",
            "production_types": ["korn", "grovfor", "korn"],
            "farm_size_range": "50_199",
            "team_size": "2_5",
            "onboarding_goals": ["regnskap", "frister"],
            "billing_method": "faktura",
            "billing_email": "faktura@solberg.no",
        },
    )

    assert response.status_code == 200
    assert response.json()["industry_code"] == "Dyrking av korn"
    assert response.json()["production_types"] == ["korn", "grovfor"]
    assert saved_farms[0]["onboarding_goals"] == ["regnskap", "frister"]
    assert saved_links[0]["user_id"] == "user-123"
    assert queries[0]["parameters"] == [{"name": "@org_number", "value": "123456789"}]


def test_create_farm_allows_manual_setup_without_an_org_number(monkeypatch):
    saved_farms = []

    class FarmsContainer:
        def query_items(self, **_kwargs):
            return []

        def upsert_item(self, item):
            saved_farms.append(item)

    class FarmUsersContainer:
        def upsert_item(self, _item):
            return None

    async def lookup_org(_org_number):
        raise AssertionError("Manual setup must not call BRREG without an organisation number")

    monkeypatch.setattr(farms, "get_farms_container", lambda: FarmsContainer())
    monkeypatch.setattr(farms, "get_farm_users_container", lambda: FarmUsersContainer())
    monkeypatch.setattr(farms.brreg_service, "lookup_org", lookup_org)

    response = make_client().post(
        "/api/farms",
        json={
            "name": "Hjemmegården",
            "org_number": "",
            "manual_entry": True,
            "primary_farm_type": "husdyr",
            "production_types": ["sau_geit"],
            "farm_size_range": "vet_ikke",
            "team_size": "1",
            "onboarding_goals": ["dokumenter"],
        },
    )

    assert response.status_code == 200
    assert response.json()["org_number"].startswith("manual-")
    assert response.json()["brreg_verified"] is False
    assert saved_farms[0]["name"] == "Hjemmegården"


def test_create_farm_rejects_unknown_onboarding_values():
    response = make_client().post(
        "/api/farms",
        json={
            "name": "Solberg gård",
            "org_number": "123456789",
            "primary_farm_type": "havbruk",
        },
    )

    assert response.status_code == 422
