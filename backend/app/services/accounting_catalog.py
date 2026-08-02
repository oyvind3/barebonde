"""Accounting helper data for account suggestions and glossary."""

from typing import Any

# Forenklet større kontoplan for bondehverdagen.
ACCOUNT_CATALOG: list[dict[str, Any]] = [
    {"code": "3000", "name": "Salgsinntekt varer", "category": "Inntekt", "simple": True},
    {"code": "3100", "name": "Tilskudd Landbruksdirektoratet", "category": "Inntekt", "simple": True},
    {"code": "3200", "name": "Leieinntekt maskin/jord", "category": "Inntekt", "simple": True},
    {"code": "3400", "name": "Annen driftsinntekt", "category": "Inntekt", "simple": True},
    {"code": "4000", "name": "Varekostnad innsatsfaktorer", "category": "Kostnad", "simple": True},
    {"code": "4010", "name": "Såkorn og planter", "category": "Kostnad", "simple": True},
    {"code": "4020", "name": "Gjødsel og kalk", "category": "Kostnad", "simple": True},
    {"code": "4030", "name": "Kraftfôr og grovfôr", "category": "Kostnad", "simple": True},
    {"code": "4040", "name": "Veterinær og dyrehelse", "category": "Kostnad", "simple": True},
    {"code": "4500", "name": "Fremmedytelser og maskinleie", "category": "Kostnad", "simple": True},
    {"code": "5000", "name": "Lønn til ansatte", "category": "Kostnad", "simple": True},
    {"code": "5400", "name": "Arbeidsgiveravgift", "category": "Kostnad", "simple": False},
    {"code": "6000", "name": "Avskrivning driftsbygning (saldogruppe h)", "category": "Kostnad", "simple": False},
    {"code": "6010", "name": "Avskrivning maskiner/redskap (saldogruppe d)", "category": "Kostnad", "simple": False},
    {"code": "6200", "name": "Diesel og drivstoff", "category": "Kostnad", "simple": True},
    {"code": "6300", "name": "Elektrisitet", "category": "Kostnad", "simple": True},
    {"code": "6340", "name": "Vann, renovasjon", "category": "Kostnad", "simple": False},
    {"code": "6500", "name": "Redskap og verktøy", "category": "Kostnad", "simple": True},
    {"code": "6700", "name": "Regnskap og rådgivning", "category": "Kostnad", "simple": True},
    {"code": "6800", "name": "Kontor/IT/telefon", "category": "Kostnad", "simple": True},
    {"code": "6990", "name": "Diverse driftskostnader", "category": "Kostnad", "simple": False},
    {"code": "7140", "name": "Transportkostnader", "category": "Kostnad", "simple": True},
    {"code": "7500", "name": "Forsikringspremie", "category": "Kostnad", "simple": True},
    {"code": "7770", "name": "Bank- og kortgebyr", "category": "Kostnad", "simple": True},
    {"code": "7790", "name": "Annen finanskostnad", "category": "Kostnad", "simple": False},
    {"code": "8150", "name": "Rentekostnad lån", "category": "Kostnad", "simple": True},
    {"code": "8300", "name": "Betalbar skatt", "category": "Skatt", "simple": False},
    {"code": "1920", "name": "Bankinnskudd", "category": "Balanse", "simple": True},
    {"code": "2400", "name": "Leverandørgjeld", "category": "Balanse", "simple": True},
    {"code": "2700", "name": "Utgående mva", "category": "MVA", "simple": True},
    {"code": "2710", "name": "Inngående mva", "category": "MVA", "simple": True},
    {"code": "2740", "name": "Oppgjørskonto mva", "category": "MVA", "simple": True},
]

GLOSSARY: list[dict[str, str]] = [
    {
        "term": "Bilag",
        "description": "Dokumentasjon på at penger har gått inn eller ut, for eksempel kvittering eller faktura.",
    },
    {
        "term": "Inngående MVA",
        "description": "MVA du betaler på kjøp. Kan ofte trekkes fra når du leverer MVA-melding.",
    },
    {
        "term": "Utgående MVA",
        "description": "MVA du legger på salg. Dette rapporteres til staten i MVA-meldingen.",
    },
    {
        "term": "Periodisering",
        "description": "Føring i perioden inntekten/kostnaden hører til, ikke nødvendigvis når betalingen skjer.",
    },
    {
        "term": "Jordbruksfradrag",
        "description": "Skattefradrag for aktiv jordbruksdrift med inntekt fra egen produksjon eller bearbeiding.",
    },
    {
        "term": "Biologiske eiendeler",
        "description": "Husdyr og avlinger vurderes etter egne regler i landbruket.",
    },
    {
        "term": "Likviditet",
        "description": "Hvor lett du kan betale regninger i tide med pengene du har tilgjengelig.",
    },
]


def get_accounts(simple_mode: bool = False) -> list[dict[str, Any]]:
    if simple_mode:
        return [account for account in ACCOUNT_CATALOG if account["simple"]]
    return ACCOUNT_CATALOG


def search_accounts(query: str, simple_mode: bool = False) -> list[dict[str, Any]]:
    source = get_accounts(simple_mode=simple_mode)
    normalized_query = query.strip().lower()
    if not normalized_query:
        return source

    return [
        account
        for account in source
        if normalized_query in account["code"].lower()
        or normalized_query in account["name"].lower()
        or normalized_query in account["category"].lower()
    ]
