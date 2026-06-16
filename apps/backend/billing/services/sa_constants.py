"""South African fintech constants and ZAR plan catalogue."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

VAT_RATE = 0.15
DEFAULT_CURRENCY = "zar"
TIMEZONE = "Africa/Johannesburg"

PROVINCE_LABELS = {
    "GAUTENG": "Gauteng",
    "WESTERN_CAPE": "Western Cape",
    "KWAZULU_NATAL": "KwaZulu-Natal",
    "EASTERN_CAPE": "Eastern Cape",
    "LIMPOPO": "Limpopo",
    "MPUMALANGA": "Mpumalanga",
    "NORTH_WEST": "North West",
    "FREE_STATE": "Free State",
    "NORTHERN_CAPE": "Northern Cape",
}

PAYMENT_RAIL_LABELS = {
    "CARD": "Card (Visa/Mastercard)",
    "EFT": "Standard EFT",
    "INSTANT_EFT": "Instant EFT (Ozow / PayFast)",
    "DEBIT_ORDER": "Debit Order (Naedo)",
    "PAYSHAP": "PayShap (RPP/RTP)",
    "RNCS": "Capitec Pay / RNCS",
}

INDUSTRY_SECTORS = [
    "Banking & Lending",
    "Payments & Wallets",
    "Insurtech",
    "Wealth & Asset Management",
    "RegTech & Compliance",
    "SME & Merchant Services",
    "Other",
]


class SaPlanDict(TypedDict):
    tier: str
    label: str
    label_af: str | None
    amount_cents: int
    vat_inclusive: bool
    description: str
    features: list[str]


SA_PLANS: list[SaPlanDict] = [
    {
        "tier": "STARTER",
        "label": "Starter",
        "label_af": "Beginner",
        "amount_cents": 49900,
        "vat_inclusive": True,
        "description": "For early-stage SA fintechs and startups",
        "features": ["Up to 500 transactions/mo", "PayFast & EFT reconciliation", "POPIA audit log"],
    },
    {
        "tier": "PRO",
        "label": "Pro",
        "label_af": "Professioneel",
        "amount_cents": 149900,
        "vat_inclusive": True,
        "description": "For growing payment platforms and neobanks",
        "features": [
            "Unlimited transactions",
            "PayShap & Instant EFT webhooks",
            "FICA/KYC workflow",
            "SARS VAT reporting",
        ],
    },
    {
        "tier": "ENTERPRISE",
        "label": "Enterprise",
        "label_af": None,
        "amount_cents": 499900,
        "vat_inclusive": True,
        "description": "For banks, PSPs, and regulated entities",
        "features": [
            "Multi-entity (CIPC groups)",
            "SARB reporting hooks",
            "Dedicated compliance SLA",
            "Peach Payments / Ozow routing",
        ],
    },
]


def plan_by_tier(tier: str) -> SaPlanDict | None:
    return next((p for p in SA_PLANS if p["tier"] == tier), None)


def extract_vat_from_inclusive(amount_cents: int) -> tuple[int, int]:
    ex_vat = round(amount_cents / (1 + VAT_RATE))
    return ex_vat, amount_cents - ex_vat


def format_zar(cents: int) -> str:
    return f"R {cents / 100:,.2f}"
