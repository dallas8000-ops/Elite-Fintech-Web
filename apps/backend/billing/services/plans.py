"""Plan catalogue with rails for checkout UI."""

from __future__ import annotations

import os

from billing.services.african_payments import EA_PRIMARY_RAILS, SA_PRIMARY_RAILS
from billing.services.fx_rates import rates_public_payload
from billing.services.payfast import is_payfast_configured
from billing.services.regional import default_currency, get_plans, is_east_africa, resolve_country
from billing.services.stripe_service import is_stripe_configured


def get_available_plans(country: str | None = None) -> list[dict]:
    code = resolve_country(country)
    cur = default_currency(code)
    flutterwave = bool(os.getenv("FLUTTERWAVE_SECRET_KEY"))
    payfast = is_payfast_configured()
    stripe = is_stripe_configured()

    if is_east_africa():
        rail_ids = [r["id"] for r in EA_PRIMARY_RAILS]
        fx = rates_public_payload()
        plans = []
        for p in get_plans(code):
            rails = []
            if flutterwave:
                rails.extend(["MOBILE_MONEY", "USSD", "CARD"])
            else:
                rails.extend(rail_ids[:2])
            if stripe:
                rails.append("CARD")
            plans.append(
                {
                    **p,
                    "currency": cur,
                    "country": code,
                    "amount_display": _format(p["amount_cents"], code),
                    "recommended_rails": list(dict.fromkeys(rails)),
                    "providers": [],
                    "pricing_mode": fx.get("pricing_mode", "static"),
                    "fx_trading_date": fx.get("trading_date"),
                    "fx_source": fx.get("source"),
                }
            )
        return plans

    sa_rail_ids = [r["id"] for r in SA_PRIMARY_RAILS if r["priority"] <= 5]
    plans = []
    for p in get_plans(code):
        rails = []
        if payfast:
            rails.extend(["INSTANT_EFT", "DEBIT_ORDER", "EFT"])
        if stripe:
            rails.append("CARD")
        plans.append(
            {
                **p,
                "currency": cur,
                "country": "ZA",
                "amount_display": _format(p["amount_cents"], code),
                "recommended_rails": rails or sa_rail_ids[:3],
                "providers": [],
            }
        )
    return plans


def _format(amount_minor: int, country: str) -> str:
    from billing.services.regional import format_money

    return format_money(amount_minor, country)
