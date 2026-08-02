"""
BRREG integration service.
Fetches and normalizes organization data from Enhetsregisteret.
"""

from typing import Any, Optional
import httpx

BRREG_BASE_URL = "https://data.brreg.no/enhetsregisteret/api/enheter"


class BrregService:
    """Service wrapper around BRREG Enhetsregisteret API."""

    def __init__(self, timeout_seconds: float = 8.0):
        self.timeout_seconds = timeout_seconds

    async def lookup_org(self, org_number: str) -> Optional[dict[str, Any]]:
        """Return normalized organization data by 9-digit org number, or None if not found."""
        cleaned = org_number.strip().replace(" ", "")
        if not cleaned.isdigit() or len(cleaned) != 9:
            raise ValueError("Organisasjonsnummer må være 9 sifre")

        url = f"{BRREG_BASE_URL}/{cleaned}"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url)

        if response.status_code == 404:
            return None

        response.raise_for_status()
        data = response.json()
        return self._normalize(data)

    async def search_orgs(self, query: str, size: int = 10) -> list[dict[str, Any]]:
        """
        Search BRREG Enhetsregisteret by name or organization number.
        Returns a list of normalized organization dicts.
        """
        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        # If 9 digits, do direct lookup first
        digits_only = cleaned_query.replace(" ", "")
        if digits_only.isdigit() and len(digits_only) == 9:
            direct = await self.lookup_org(digits_only)
            if direct:
                return [direct]

        # Search by name or partial string using BRREG search endpoint
        params = {
            "navn": cleaned_query,
            "navnMetodeForSoek": "FORTLOEPENDE",
            "size": min(size, 20),
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(BRREG_BASE_URL, params=params)

        response.raise_for_status()
        json_data = response.json()

        embedded = json_data.get("_embedded") or {}
        enheter = embedded.get("enheter") or []

        return [self._normalize(data) for data in enheter]

    def _normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        address_data = data.get("forretningsadresse") or data.get("postadresse") or {}
        address_lines = address_data.get("adresse") or []

        org_form_obj = data.get("organisasjonsform") or {}
        org_form_code = org_form_obj.get("kode", "")
        org_form_desc = org_form_obj.get("beskrivelse", "")
        org_form_str = f"{org_form_desc} ({org_form_code})" if org_form_code and org_form_desc else (org_form_desc or org_form_code)

        naering_obj = data.get("naeringskode1") or {}
        naering_code = naering_obj.get("kode", "")
        naering_desc = naering_obj.get("beskrivelse", "")
        naering_str = f"{naering_desc} ({naering_code})" if naering_code and naering_desc else (naering_desc or naering_code)

        mva = data.get("registrertIMvaregisteret")
        mva_str = "Ja" if mva is True else ("Nei" if mva is False else "Ukjent")

        reg_date = data.get("registreringsdatoEnhetsregisteret", "")
        if reg_date and len(reg_date) == 10 and "-" in reg_date:
            parts = reg_date.split("-")
            reg_date_formatted = f"{parts[2]}.{parts[1]}.{parts[0]}"
        else:
            reg_date_formatted = reg_date

        return {
            "org_number": data.get("organisasjonsnummer", ""),
            "name": data.get("navn", ""),
            "organization_form": org_form_str,
            "postal_code": address_data.get("postnummer", ""),
            "city": address_data.get("poststed", ""),
            "municipality": address_data.get("kommune", ""),
            "address": ", ".join(address_lines),
            "is_active": not data.get("slettedato"),
            "registered_mva": mva_str,
            "industry_code": naering_str,
            "registered_date": reg_date_formatted,
        }


brreg_service = BrregService()
