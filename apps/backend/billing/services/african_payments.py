"""
African payment domain model — Uganda (default) is mobile-money-first.

Uganda reality:
  • MTN Mobile Money and Airtel Money dominate — not cards or PayFast
  • Flutterwave / Pesapal / Yo! Payments aggregate MoMo + cards
  • USSD (*165#, *185#) still used on feature phones
  • Bank of Uganda licenses payment service providers
  • UGX billing; 18% VAT via URA

South Africa rails (PayFast, PayShap, EFT) remain available when MARKET=ZA.
"""

from __future__ import annotations

from typing import TypedDict


class RailInfo(TypedDict):
    id: str
    label: str
    region: str
    settlement: str
    typical_use: str
    western_equivalent: str | None
    providers: list[str]
    is_async: bool
    priority: int  # lower = more common in SA fintech


class MarketContext(TypedDict):
    id: str
    label: str
    primary_rails: list[str]
    note: str


# ── Rail catalogue (ordered for SA; pan-African rails included for expansion) ──

AFRICAN_PAYMENT_RAILS: list[RailInfo] = [
    {
        "id": "INSTANT_EFT",
        "label": "Instant EFT",
        "region": "ZA",
        "settlement": "Near real-time (seconds–minutes)",
        "typical_use": "Online checkout — customer authorises at their bank app",
        "western_equivalent": "Open banking / Pay by Bank (not card)",
        "providers": ["OZOW", "PAYFAST", "STITCH"],
        "is_async": False,
        "priority": 1,
    },
    {
        "id": "PAYSHAP",
        "label": "PayShap (RPP)",
        "region": "ZA",
        "settlement": "Real-time account-to-account",
        "typical_use": "Instant payments by mobile number or QR — SARB-led rail",
        "western_equivalent": "FedNow / SEPA Instant (not cards)",
        "providers": ["BANKS", "PEACH_PAYMENTS"],
        "is_async": False,
        "priority": 2,
    },
    {
        "id": "DEBIT_ORDER",
        "label": "Debit Order (DebiCheck)",
        "region": "ZA",
        "settlement": "Batch collection (T+1 to T+3)",
        "typical_use": "Recurring subscriptions & mandates — SA's answer to card billing",
        "western_equivalent": "ACH direct debit (not card subscription)",
        "providers": ["PAYFAST", "PEACH_PAYMENTS", "BANKS"],
        "is_async": True,
        "priority": 3,
    },
    {
        "id": "EFT",
        "label": "Standard EFT",
        "region": "ZA",
        "settlement": "1–3 business days",
        "typical_use": "B2B invoices, manual bank transfers with reference",
        "western_equivalent": "Wire / slow ACH",
        "providers": ["BANKS"],
        "is_async": True,
        "priority": 4,
    },
    {
        "id": "RNCS",
        "label": "Capitec Pay / RNCS",
        "region": "ZA",
        "settlement": "Near real-time",
        "typical_use": "Retail bank push payment — huge SA user base",
        "western_equivalent": None,
        "providers": ["CAPITEC", "OZOW"],
        "is_async": False,
        "priority": 5,
    },
    {
        "id": "CARD",
        "label": "Card (Visa/Mastercard)",
        "region": "PAN",
        "settlement": "T+1 to T+3 (acquirer dependent)",
        "typical_use": "Cross-border, diaspora, tourists — less dominant locally",
        "western_equivalent": "Primary US/EU online rail",
        "providers": ["PAYFAST", "PEACH_PAYMENTS", "STRIPE"],
        "is_async": False,
        "priority": 6,
    },
    {
        "id": "MOBILE_MONEY",
        "label": "Mobile Money",
        "region": "KE, GH, TZ, UG, RW…",
        "settlement": "Instant wallet-to-wallet",
        "typical_use": "M-Pesa, MTN MoMo, Airtel Money — dominant in East/West Africa",
        "western_equivalent": "No direct equivalent (Venmo scale × unbanked)",
        "providers": ["MPESA", "MTN_MOMO", "AIRTEL"],
        "is_async": False,
        "priority": 7,
    },
    {
        "id": "USSD",
        "label": "USSD (*120#)",
        "region": "PAN-AFRICA",
        "settlement": "Real-time session",
        "typical_use": "Feature-phone banking — no smartphone or data required",
        "western_equivalent": None,
        "providers": ["TELCOS", "BANKS", "MPESA"],
        "is_async": False,
        "priority": 8,
    },
    {
        "id": "AGENT_CASH",
        "label": "Agent Cash-In / Cash-Out",
        "region": "PAN-AFRICA",
        "settlement": "Immediate at agent",
        "typical_use": "Convert cash ↔ wallet/bank — last-mile for unbanked",
        "western_equivalent": None,
        "providers": ["MPESA_AGENTS", "MTN_AGENTS", "SHOPRITE_MONEY_MARKET"],
        "is_async": False,
        "priority": 9,
    },
]

RAIL_BY_ID = {r["id"]: r for r in AFRICAN_PAYMENT_RAILS}

SA_PRIMARY_RAILS = [r for r in AFRICAN_PAYMENT_RAILS if r["region"] in ("ZA", "PAN") and r["priority"] <= 6]

# East Africa — MoMo first (Uganda, Kenya, Rwanda, Tanzania)
EA_PRIMARY_RAILS = [
    next(r for r in AFRICAN_PAYMENT_RAILS if r["id"] == "MOBILE_MONEY"),
    next(r for r in AFRICAN_PAYMENT_RAILS if r["id"] == "USSD"),
    next(r for r in AFRICAN_PAYMENT_RAILS if r["id"] == "AGENT_CASH"),
    next(r for r in AFRICAN_PAYMENT_RAILS if r["id"] == "CARD"),
]

MARKET_CONTEXT: list[MarketContext] = [
    {
        "id": "UG",
        "label": "Uganda",
        "primary_rails": ["MOBILE_MONEY", "USSD", "AGENT_CASH", "CARD"],
        "note": "MTN MoMo & Airtel Money; Flutterwave/Pesapal; Bank of Uganda PSPs.",
    },
    {
        "id": "KE",
        "label": "Kenya",
        "primary_rails": ["MOBILE_MONEY", "USSD", "AGENT_CASH"],
        "note": "M-Pesa dominant; Pesapal/Flutterwave for online; CBK-regulated.",
    },
    {
        "id": "RW",
        "label": "Rwanda",
        "primary_rails": ["MOBILE_MONEY", "USSD", "AGENT_CASH"],
        "note": "MTN MoMo & Airtel; NBR-licensed wallets and agents.",
    },
    {
        "id": "TZ",
        "label": "Tanzania",
        "primary_rails": ["MOBILE_MONEY", "USSD", "AGENT_CASH"],
        "note": "M-Pesa, Tigo Pesa, Airtel; BoT mobile money oversight.",
    },
    {
        "id": "US_EU",
        "label": "USA / Europe",
        "primary_rails": ["CARD", "ACH", "SEPA"],
        "note": "Card-on-file subscriptions — not the East Africa default.",
    },
    {
        "id": "ZA",
        "label": "South Africa (legacy)",
        "primary_rails": ["INSTANT_EFT", "PAYSHAP", "DEBIT_ORDER", "EFT", "RNCS"],
        "note": "Optional legacy market — volatile FX/load-shedding environment; use MARKET=ZA.",
    },
    {
        "id": "WEST_AFRICA",
        "label": "West Africa",
        "primary_rails": ["MOBILE_MONEY", "USSD", "AGENT_CASH", "CARD"],
        "note": "MTN MoMo, Orange Money; fragmented rails per country.",
    },
]

RAIL_PROVIDER_MAP: dict[str, str] = {
    "MOBILE_MONEY": "FLUTTERWAVE",
    "USSD": "FLUTTERWAVE",
    "AGENT_CASH": "MTN_MOMO",
    "CARD": "FLUTTERWAVE",
    "INSTANT_EFT": "PAYFAST",
    "DEBIT_ORDER": "PAYFAST",
    "EFT": "PAYFAST",
    "PAYSHAP": "PEACH_PAYMENTS",
    "RNCS": "OZOW",
}


def _primary_rails() -> list[RailInfo]:
    from billing.services.regional import is_east_africa

    return EA_PRIMARY_RAILS if is_east_africa() else SA_PRIMARY_RAILS


def rails_for_checkout() -> list[dict]:
    import os

    from billing.services.payfast import is_payfast_configured
    from billing.services.regional import is_east_africa, is_south_africa
    from billing.services.stripe_service import is_stripe_configured

    payfast = is_payfast_configured()
    stripe = is_stripe_configured()
    flutterwave = bool(os.getenv("FLUTTERWAVE_SECRET_KEY"))

    result = []
    for rail in _primary_rails():
        providers = []
        if is_east_africa():
            if rail["id"] in ("MOBILE_MONEY", "USSD", "CARD") and flutterwave:
                providers.append("FLUTTERWAVE")
            if rail["id"] in ("MOBILE_MONEY", "AGENT_CASH"):
                providers.append("MTN_MOMO")
            if rail["id"] == "CARD" and stripe:
                providers.append("STRIPE")
        elif is_south_africa():
            if rail["id"] in ("INSTANT_EFT", "DEBIT_ORDER", "EFT", "CARD") and payfast:
                providers.append("PAYFAST")
            if rail["id"] == "CARD" and stripe:
                providers.append("STRIPE")
            if rail["id"] == "PAYSHAP":
                providers.append("PEACH_PAYMENTS")
            if rail["id"] == "RNCS":
                providers.append("OZOW")

        result.append(
            {
                **rail,
                "available": len(providers) > 0
                or (is_east_africa() and rail["id"] in ("MOBILE_MONEY", "USSD")),
                "checkout_providers": providers,
            }
        )
    return result


def resolve_checkout(rail: str, provider: str | None = None) -> tuple[str, str]:
    if rail not in RAIL_BY_ID:
        raise ValueError(f"Unknown payment rail: {rail}")
    if provider:
        return rail, provider
    return rail, RAIL_PROVIDER_MAP.get(rail, "FLUTTERWAVE")
