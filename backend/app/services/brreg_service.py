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
        """Return normalized organization data, or None if not found."""
        if not org_number.isdigit() or len(org_number) != 9:
            raise ValueError("Organisasjonsnummer må være 9 sifre")

        url = f"{BRREG_BASE_URL}/{org_number}"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url)

        if response.status_code == 404:
            return None

        response.raise_for_status()
        data = response.json()
        return self._normalize(data)

    def _normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        address_data = data.get("forretningsadresse") or {}
        address_lines = address_data.get("adresse") or []

        return {
            "org_number": data.get("organisasjonsnummer", ""),
            "name": data.get("navn", ""),
            "organization_form": (data.get("organisasjonsform") or {}).get("beskrivelse", ""),
            "postal_code": address_data.get("postnummer", ""),
            "city": address_data.get("poststed", ""),
            "municipality": address_data.get("kommune", ""),
            "address": ", ".join(address_lines),
        }


brreg_service = BrregService()
