"""
East Africa market — Uganda, Kenya, Rwanda, Tanzania.

Mobile-money-first billing. Plans can track daily FX from USD anchors (FX_PRICING_ENABLED).
South Africa is optional legacy (MARKET=ZA) — not the default.
"""

from __future__ import annotations

from billing.services.sa_constants import SaPlanDict

# ISO 3166-1 alpha-2
EAST_AFRICA_COUNTRIES: dict[str, dict] = {
    "UG": {
        "label": "Uganda",
        "currency": "ugx",
        "currency_label": "UGX",
        "vat_rate": 0.18,
        "timezone": "Africa/Kampala",
        "regulator": "Bank of Uganda",
        "compliance": "Data Protection and Privacy Act 2019",
        "company_reg_label": "URSB registration (optional)",
        "vat_label": "URA TIN (optional)",
        "regions": {
            "CENTRAL": "Central (Kampala)",
            "EASTERN": "Eastern",
            "NORTHERN": "Northern",
            "WESTERN": "Western",
        },
        "momo_providers": ["MTN MoMo", "Airtel Money"],
    },
    "KE": {
        "label": "Kenya",
        "currency": "kes",
        "currency_label": "KES",
        "vat_rate": 0.16,
        "timezone": "Africa/Nairobi",
        "regulator": "Central Bank of Kenya",
        "compliance": "Data Protection Act 2019",
        "company_reg_label": "Business registration (optional)",
        "vat_label": "KRA PIN (optional)",
        "regions": {
            "NAIROBI": "Nairobi",
            "COAST": "Coast",
            "CENTRAL": "Central",
            "RIFT_VALLEY": "Rift Valley",
            "EASTERN": "Eastern",
            "WESTERN": "Western",
            "NORTH_EASTERN": "North Eastern",
        },
        "momo_providers": ["M-Pesa", "Airtel Money"],
    },
    "RW": {
        "label": "Rwanda",
        "currency": "rwf",
        "currency_label": "RWF",
        "vat_rate": 0.18,
        "timezone": "Africa/Kigali",
        "regulator": "National Bank of Rwanda",
        "compliance": "Law No. 058/2021 on data protection",
        "company_reg_label": "RDB registration (optional)",
        "vat_label": "RRA TIN (optional)",
        "regions": {
            "KIGALI": "Kigali",
            "EASTERN": "Eastern",
            "NORTHERN": "Northern",
            "SOUTHERN": "Southern",
            "WESTERN": "Western",
        },
        "momo_providers": ["MTN MoMo", "Airtel Money"],
    },
    "TZ": {
        "label": "Tanzania",
        "currency": "tzs",
        "currency_label": "TZS",
        "vat_rate": 0.18,
        "timezone": "Africa/Dar_es_Salaam",
        "regulator": "Bank of Tanzania",
        "compliance": "Personal Data Protection Act 2022",
        "company_reg_label": "BRELA registration (optional)",
        "vat_label": "TRA TIN (optional)",
        "regions": {
            "DAR_ES_SALAAM": "Dar es Salaam",
            "ARUSHA": "Arusha",
            "MWANZA": "Mwanza",
            "DODOMA": "Dodoma",
            "ZANZIBAR": "Zanzibar",
        },
        "momo_providers": ["M-Pesa", "Tigo Pesa", "Airtel Money"],
    },
}

DEFAULT_COUNTRY = "UG"

# Monthly plan amounts in local minor units (UGX/RWF/TZS have no cents; KES uses cents)
TIER_AMOUNTS: dict[str, dict[str, int]] = {
    "STARTER": {"UG": 180_000, "KE": 55_000, "RW": 45_000, "TZ": 120_000},
    "PRO": {"UG": 550_000, "KE": 165_000, "RW": 135_000, "TZ": 360_000},
    "ENTERPRISE": {"UG": 1_850_000, "KE": 550_000, "RW": 450_000, "TZ": 1_200_000},
}

TIER_META: dict[str, dict] = {
    "STARTER": {
        "label": "Starter",
        "description": "Early-stage fintechs, SACCOs, and agent networks",
        "features": [
            "Up to 500 MoMo transactions/mo",
            "MTN / M-Pesa / Airtel reconciliation",
            "Data protection audit log",
        ],
    },
    "PRO": {
        "label": "Pro",
        "description": "Growing wallets, lenders, and payment platforms",
        "features": [
            "Unlimited MoMo + USSD webhooks",
            "Flutterwave / Pesapal routing",
            "KYC workflow",
            "Local VAT reporting",
        ],
    },
    "ENTERPRISE": {
        "label": "Enterprise",
        "description": "Banks, telcos, and licensed PSPs",
        "features": [
            "Multi-entity groups",
            "Central bank reporting hooks",
            "Dedicated compliance SLA",
            "Agent network settlement",
        ],
    },
}


def country_codes() -> list[str]:
    return list(EAST_AFRICA_COUNTRIES.keys())


def country_meta(code: str) -> dict:
    return EAST_AFRICA_COUNTRIES.get(code.upper(), EAST_AFRICA_COUNTRIES[DEFAULT_COUNTRY])


def plans_for_country(country: str) -> list[SaPlanDict]:
    code = country.upper() if country.upper() in EAST_AFRICA_COUNTRIES else DEFAULT_COUNTRY
    meta = country_meta(code)
    plans: list[SaPlanDict] = []
    for tier, amounts in TIER_AMOUNTS.items():
        info = TIER_META[tier]
        plans.append(
            {
                "tier": tier,
                "label": info["label"],
                "label_af": None,
                "amount_cents": amounts[code],
                "vat_inclusive": True,
                "description": f"{info['description']} — {meta['label']}",
                "features": info["features"],
            }
        )
    return plans


def format_amount(amount_minor: int, currency: str) -> str:
    cur = currency.lower()
    if cur == "ugx":
        return f"USh {amount_minor:,}"
    if cur == "rwf":
        return f"FRw {amount_minor:,}"
    if cur == "tzs":
        return f"TSh {amount_minor:,}"
    if cur == "kes":
        return f"KSh {amount_minor / 100:,.2f}"
    return f"{amount_minor:,} {currency.upper()}"
