"""Uganda fintech constants — UGX, MTN MoMo, Kampala operations."""

from __future__ import annotations

from billing.services.sa_constants import SaPlanDict

VAT_RATE = 0.18  # Uganda VAT
DEFAULT_CURRENCY = "ugx"
TIMEZONE = "Africa/Kampala"

UG_REGIONS = {
    "CENTRAL": "Central (Kampala)",
    "EASTERN": "Eastern",
    "NORTHERN": "Northern",
    "WESTERN": "Western",
}

# UGX amounts stored in minor units (1 UGX = 1 unit; no cents in practice)
UG_PLANS: list[SaPlanDict] = [
    {
        "tier": "STARTER",
        "label": "Starter",
        "label_af": None,
        "amount_cents": 180_000,
        "vat_inclusive": True,
        "description": "For early-stage Ugandan fintechs and SACCOs",
        "features": [
            "Up to 500 MoMo transactions/mo",
            "MTN & Airtel reconciliation",
            "Data protection audit log",
        ],
    },
    {
        "tier": "PRO",
        "label": "Pro",
        "label_af": None,
        "amount_cents": 550_000,
        "vat_inclusive": True,
        "description": "For growing wallets and payment platforms",
        "features": [
            "Unlimited MoMo + USSD webhooks",
            "Flutterwave / Pesapal routing",
            "KYC workflow",
            "URA VAT reporting",
        ],
    },
    {
        "tier": "ENTERPRISE",
        "label": "Enterprise",
        "label_af": None,
        "amount_cents": 1_850_000,
        "vat_inclusive": True,
        "description": "For banks, telcos, and licensed PSPs",
        "features": [
            "Multi-entity (URSB groups)",
            "Bank of Uganda reporting hooks",
            "Dedicated compliance SLA",
            "Agent network settlement",
        ],
    },
]


def format_ugx(amount: int) -> str:
    return f"USh {amount:,}"
