"""Accounting helper data: account catalog, account helpers, VAT catalog.

The account catalog is intentionally a small, simplified chart of accounts for
Barebonde MVP -- not a complete standard Norwegian chart of accounts.
"""

from typing import Any, Optional

# Account types used by the journal engine and reports.
ACCOUNT_TYPE_ASSET = "asset"
ACCOUNT_TYPE_LIABILITY = "liability"
ACCOUNT_TYPE_EQUITY = "equity"
ACCOUNT_TYPE_INCOME = "income"
ACCOUNT_TYPE_EXPENSE = "expense"
ACCOUNT_TYPE_VAT = "vat"

# Forenklet kontoplan for bondehverdagen.
ACCOUNT_CATALOG: list[dict[str, Any]] = [
    # Balanse -- eiendeler
    {"code": "1500", "name": "Kundefordringer", "category": "Balanse", "account_type": ACCOUNT_TYPE_ASSET, "normal_balance": "debit", "simple": True},
    {"code": "1920", "name": "Bankinnskudd", "category": "Balanse", "account_type": ACCOUNT_TYPE_ASSET, "normal_balance": "debit", "simple": True, "is_cash_account": True},
    # Balanse -- gjeld
    {"code": "2400", "name": "Leverandørgjeld", "category": "Balanse", "account_type": ACCOUNT_TYPE_LIABILITY, "normal_balance": "credit", "simple": True},
    # MVA-kontoer
    {"code": "2700", "name": "Utgående mva", "category": "MVA", "account_type": ACCOUNT_TYPE_VAT, "normal_balance": "credit", "simple": True},
    {"code": "2710", "name": "Inngående mva", "category": "MVA", "account_type": ACCOUNT_TYPE_VAT, "normal_balance": "debit", "simple": True},
    {"code": "2740", "name": "Oppgjørskonto mva", "category": "MVA", "account_type": ACCOUNT_TYPE_VAT, "normal_balance": "credit", "simple": True},
    # Inntekt
    {"code": "3000", "name": "Salgsinntekt varer", "category": "Inntekt", "account_type": ACCOUNT_TYPE_INCOME, "normal_balance": "credit", "simple": True},
    {"code": "3100", "name": "Tilskudd Landbruksdirektoratet", "category": "Inntekt", "account_type": ACCOUNT_TYPE_INCOME, "normal_balance": "credit", "simple": True},
    {"code": "3200", "name": "Leieinntekt maskin/jord", "category": "Inntekt", "account_type": ACCOUNT_TYPE_INCOME, "normal_balance": "credit", "simple": True},
    {"code": "3400", "name": "Annen driftsinntekt", "category": "Inntekt", "account_type": ACCOUNT_TYPE_INCOME, "normal_balance": "credit", "simple": True},
    # Kostnad
    {"code": "4000", "name": "Varekostnad innsatsfaktorer", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": True},
    {"code": "4010", "name": "Såkorn og planter", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": True},
    {"code": "4020", "name": "Gjødsel og kalk", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": True},
    {"code": "4030", "name": "Kraftfôr og grovfôr", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": True},
    {"code": "4040", "name": "Veterinær og dyrehelse", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": True},
    {"code": "4500", "name": "Fremmedytelser og maskinleie", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": True},
    {"code": "5000", "name": "Lønn til ansatte", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": True},
    {"code": "5400", "name": "Arbeidsgiveravgift", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": False},
    {"code": "6000", "name": "Avskrivning driftsbygning (saldogruppe h)", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": False},
    {"code": "6010", "name": "Avskrivning maskiner/redskap (saldogruppe d)", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": False},
    {"code": "6200", "name": "Diesel og drivstoff", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": True},
    {"code": "6300", "name": "Elektrisitet", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": True},
    {"code": "6340", "name": "Vann, renovasjon", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": False},
    {"code": "6500", "name": "Redskap og verktøy", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": True},
    {"code": "6700", "name": "Regnskap og rådgivning", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": True},
    {"code": "6800", "name": "Kontor/IT/telefon", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": True},
    {"code": "6990", "name": "Diverse driftskostnader", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": False},
    {"code": "7140", "name": "Transportkostnader", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": True},
    {"code": "7500", "name": "Forsikringspremie", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": True},
    {"code": "7770", "name": "Bank- og kortgebyr", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": True},
    {"code": "7790", "name": "Annen finanskostnad", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": False},
    {"code": "8150", "name": "Rentekostnad lån", "category": "Kostnad", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": True},
    {"code": "8300", "name": "Betalbar skatt", "category": "Skatt", "account_type": ACCOUNT_TYPE_EXPENSE, "normal_balance": "debit", "simple": False},
]

_ACCOUNTS_BY_CODE: dict[str, dict[str, Any]] = {account["code"]: account for account in ACCOUNT_CATALOG}

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


# ---------------------------------------------------------------------------
# Account helpers
# ---------------------------------------------------------------------------

def get_account(code: Optional[str]) -> Optional[dict[str, Any]]:
    """Return the catalog entry for an account code, or None if unknown."""
    if not code:
        return None
    return _ACCOUNTS_BY_CODE.get(str(code).strip())


def account_exists(code: Optional[str]) -> bool:
    return get_account(code) is not None


def _account_type(code: Optional[str]) -> Optional[str]:
    account = get_account(code)
    return account.get("account_type") if account else None


def is_income_account(code: Optional[str]) -> bool:
    return _account_type(code) == ACCOUNT_TYPE_INCOME


def is_expense_account(code: Optional[str]) -> bool:
    return _account_type(code) == ACCOUNT_TYPE_EXPENSE


def is_balance_account(code: Optional[str]) -> bool:
    return _account_type(code) in {ACCOUNT_TYPE_ASSET, ACCOUNT_TYPE_LIABILITY, ACCOUNT_TYPE_EQUITY}


def is_cash_account(code: Optional[str]) -> bool:
    account = get_account(code)
    return bool(account and account.get("is_cash_account"))


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


# ---------------------------------------------------------------------------
# Internal VAT catalog
# ---------------------------------------------------------------------------

VAT_CATALOG: dict[str, dict[str, Any]] = {
    "none": {"code": "none", "direction": "none", "rate": 0, "control_account": None},
    "input_25": {"code": "input_25", "direction": "input", "rate": 25, "control_account": "2710"},
    "input_15": {"code": "input_15", "direction": "input", "rate": 15, "control_account": "2710"},
    "input_12": {"code": "input_12", "direction": "input", "rate": 12, "control_account": "2710"},
    "input_0": {"code": "input_0", "direction": "input", "rate": 0, "control_account": "2710"},
    "output_25": {"code": "output_25", "direction": "output", "rate": 25, "control_account": "2700"},
    "output_15": {"code": "output_15", "direction": "output", "rate": 15, "control_account": "2700"},
    "output_12": {"code": "output_12", "direction": "output", "rate": 12, "control_account": "2700"},
    "output_0": {"code": "output_0", "direction": "output", "rate": 0, "control_account": "2700"},
}


def get_vat_code(code: Optional[str]) -> Optional[dict[str, Any]]:
    if not code:
        return None
    return VAT_CATALOG.get(str(code).strip())


def vat_code_exists(code: Optional[str]) -> bool:
    return get_vat_code(code) is not None


def normalize_legacy_vat_code(code: Optional[str], direction: str = "input") -> Optional[str]:
    """Map legacy free-text/numeric VAT codes to the internal VAT catalog.

    Returns None when the code is unknown or ambiguous -- callers must treat
    that as "needs review", never guess aggressively.
    """
    if not code:
        return None
    normalized = str(code).strip().lower()
    if normalized in VAT_CATALOG:
        return normalized
    if normalized in {"", "ingen", "none", "0", "0%", "uten mva", "unntatt"}:
        return "none"
    if direction not in {"input", "output"}:
        return None

    # Numeric rate codes: "25", "25%", "mva 25"
    rate: Optional[int] = None
    if "25" in normalized:
        rate = 25
    elif "15" in normalized:
        rate = 15
    elif "12" in normalized:
        rate = 12
    elif normalized in {"0", "0%"}:
        rate = 0

    if rate is None:
        return None
    return f"{direction}_{rate}"