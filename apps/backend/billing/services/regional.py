"""
Regional configuration — East Africa default (UG, KE, RW, TZ).

Set MARKET=ZA only if you need legacy South Africa rails (PayFast, PayShap).
"""

from __future__ import annotations

import os

from billing.services import east_africa_constants, sa_constants
from billing.services.fx_rates import rates_public_payload
from billing.services.sa_constants import SaPlanDict

DEFAULT_MARKET = "EA"


def get_market() -> str:
    return os.getenv("MARKET", DEFAULT_MARKET).upper()


def is_east_africa() -> bool:
    return get_market() in ("EA", "UG", "KE", "RW", "TZ", "EAST_AFRICA")


def is_south_africa() -> bool:
    return get_market() == "ZA"


def default_country() -> str:
    explicit = os.getenv("DEFAULT_COUNTRY", "").upper()
    if explicit in east_africa_constants.EAST_AFRICA_COUNTRIES:
        return explicit
    market = get_market()
    if market in east_africa_constants.EAST_AFRICA_COUNTRIES:
        return market
    return east_africa_constants.DEFAULT_COUNTRY


def resolve_country(code: str | None) -> str:
    if code and code.upper() in east_africa_constants.EAST_AFRICA_COUNTRIES:
        return code.upper()
    return default_country()


def vat_rate(country: str | None = None) -> float:
    if is_south_africa():
        return sa_constants.VAT_RATE
    return east_africa_constants.country_meta(resolve_country(country))["vat_rate"]


def default_currency(country: str | None = None) -> str:
    if is_south_africa():
        return sa_constants.DEFAULT_CURRENCY
    return east_africa_constants.country_meta(resolve_country(country))["currency"]


def timezone(country: str | None = None) -> str:
    if is_south_africa():
        return sa_constants.TIMEZONE
    return east_africa_constants.country_meta(resolve_country(country))["timezone"]


def get_plans(country: str | None = None) -> list[SaPlanDict]:
    if is_south_africa():
        return sa_constants.SA_PLANS
    from billing.services.market_pricing import get_market_plans

    return get_market_plans(country)


def plan_by_tier(tier: str, country: str | None = None) -> SaPlanDict | None:
    return next((p for p in get_plans(country) if p["tier"] == tier), None)


def extract_vat_from_inclusive(amount_minor: int, country: str | None = None) -> tuple[int, int]:
    rate = vat_rate(country)
    ex_vat = round(amount_minor / (1 + rate))
    return ex_vat, amount_minor - ex_vat


def format_money(amount_minor: int, country: str | None = None) -> str:
    if is_south_africa():
        return sa_constants.format_zar(amount_minor)
    cur = default_currency(country)
    return east_africa_constants.format_amount(amount_minor, cur)


def region_choices(country: str | None = None) -> list[tuple[str, str]]:
    if is_south_africa():
        return list(sa_constants.PROVINCE_LABELS.items())
    meta = east_africa_constants.country_meta(resolve_country(country))
    return list(meta["regions"].items())


def registration_labels(country: str | None = None) -> dict:
    if is_south_africa():
        return {
            "market": "ZA",
            "consent_field": "data_consent",
            "consent_label": "POPIA (South Africa)",
            "company_reg_label": "CIPC registration (optional)",
            "company_reg_placeholder": "2021/123456/07",
            "vat_label": "SARS VAT number (optional)",
            "vat_placeholder": "4123456789",
            "compliance_body": "SARB / FICA",
            "region_label": "Province",
        }
    meta = east_africa_constants.country_meta(resolve_country(country))
    return {
        "market": "EA",
        "country": resolve_country(country),
        "country_label": meta["label"],
        "consent_field": "data_consent",
        "consent_label": meta["compliance"],
        "company_reg_label": meta["company_reg_label"],
        "company_reg_placeholder": "",
        "vat_label": meta["vat_label"],
        "vat_placeholder": "",
        "compliance_body": meta["regulator"],
        "region_label": "Region",
        "currency": meta["currency"],
        "currency_label": meta["currency_label"],
    }


def market_summary() -> dict:
    if is_south_africa():
        return {
            "market": "ZA",
            "label": "South Africa (legacy)",
            "note": "Optional — PayFast / PayShap. East Africa is the primary market.",
            "countries": [],
            "default_country": None,
        }
    return {
        "market": "EA",
        "label": "East Africa",
        "note": "Uganda, Kenya, Rwanda, Tanzania — prices track daily FX from USD anchors.",
        "pricing": rates_public_payload(),
        "usd_anchors": {
            tier: float(os.getenv(f"USD_PRICE_{tier}", str(default)))
            for tier, default in [("STARTER", 12), ("PRO", 35), ("ENTERPRISE", 120)]
        },
        "default_country": default_country(),
        "countries": [
            {
                "code": code,
                "label": meta["label"],
                "currency": meta["currency"],
                "currency_label": meta["currency_label"],
                "plans": plans_for_public(code),
            }
            for code, meta in east_africa_constants.EAST_AFRICA_COUNTRIES.items()
        ],
    }


def plans_for_public(country: str) -> list[dict]:
    from billing.services.fx_rates import fx_pricing_enabled

    code = resolve_country(country)
    cur = default_currency(code)
    fx = rates_public_payload() if fx_pricing_enabled() else None
    return [
        {
            **p,
            "currency": cur,
            "amount_display": format_money(p["amount_cents"], code),
            "pricing_mode": fx.get("pricing_mode", "static") if fx else "static",
        }
        for p in get_plans(code)
    ]
