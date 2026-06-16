"""
Convert USD plan anchors to local East Africa prices using daily FX rates.
"""

from __future__ import annotations

from billing.services import east_africa_constants
from billing.services.fx_rates import fx_pricing_enabled, get_latest_snapshot, rate_for_currency
from billing.services.sa_constants import SaPlanDict

# Monthly subscription anchors in USD (ex-VAT; VAT applied after conversion)
USD_TIER_ANCHORS: dict[str, float] = {
    "STARTER": float(__import__("os").getenv("USD_PRICE_STARTER", "12")),
    "PRO": float(__import__("os").getenv("USD_PRICE_PRO", "35")),
    "ENTERPRISE": float(__import__("os").getenv("USD_PRICE_ENTERPRISE", "120")),
}


def _round_local(amount: float, currency: str) -> int:
    """MoMo-friendly rounding — whole shillings / round thousands."""
    cur = currency.lower()
    if cur in ("ugx", "rwf", "tzs"):
        step = 1000 if amount >= 10_000 else 500
        return int(round(amount / step) * step)
    if cur in ("kes", "zar"):
        # minor units (cents)
        major = amount
        step_major = 50 if major >= 500 else 10
        rounded_major = round(major / step_major) * step_major
        return int(rounded_major * 100)
    return int(round(amount))


def usd_to_minor(usd: float, currency: str, rate: float | None = None) -> int:
    cur = currency.lower()
    fx = rate if rate is not None else rate_for_currency(cur)
    local_major = usd * fx
    if cur in ("kes", "zar"):
        return _round_local(local_major, cur)
    return _round_local(local_major, cur)


def plans_for_country_market(country: str) -> tuple[list[SaPlanDict], dict]:
    code = country.upper()
    if code not in east_africa_constants.EAST_AFRICA_COUNTRIES:
        code = east_africa_constants.DEFAULT_COUNTRY
    meta = east_africa_constants.country_meta(code)
    currency = meta["currency"]
    snapshot = get_latest_snapshot()

    plans: list[SaPlanDict] = []
    for tier, usd in USD_TIER_ANCHORS.items():
        info = east_africa_constants.TIER_META[tier]
        rate = rate_for_currency(currency, snapshot)
        amount_minor = usd_to_minor(usd, currency, rate)
        # VAT-inclusive local price
        vat_rate = meta["vat_rate"]
        amount_inclusive = int(round(amount_minor * (1 + vat_rate)))

        plans.append(
            {
                "tier": tier,
                "label": info["label"],
                "label_af": None,
                "amount_cents": amount_inclusive,
                "vat_inclusive": True,
                "description": f"{info['description']} — {meta['label']}",
                "features": info["features"],
            }
        )

    fx_meta = {
        "usd_anchor_tier": USD_TIER_ANCHORS,
        "fx_rate": rate_for_currency(currency, snapshot),
        "currency": currency,
        "country": code,
    }
    if snapshot:
        fx_meta["trading_date"] = snapshot.trading_date.isoformat()
        fx_meta["fetched_at"] = snapshot.fetched_at.isoformat()
        fx_meta["source"] = snapshot.source

    return plans, fx_meta


def get_market_plans(country: str | None) -> list[SaPlanDict]:
    from billing.services.regional import is_south_africa, resolve_country

    if is_south_africa() or not fx_pricing_enabled():
        from billing.services import east_africa_constants, sa_constants

        if is_south_africa():
            return sa_constants.SA_PLANS
        return east_africa_constants.plans_for_country(resolve_country(country))

    plans, _ = plans_for_country_market(resolve_country(country))
    return plans
