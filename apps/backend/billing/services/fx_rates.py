"""
Daily FX rate fetch for East Africa pricing.

Uses open.er-api.com (free, no API key). Rates refresh once per 24h or via:
  python manage.py refresh_market_rates
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

from django.db import transaction

from billing.models import FxRateSnapshot

logger = logging.getLogger(__name__)

FX_API_URL = os.getenv("FX_API_URL", "https://open.er-api.com/v6/latest/USD")
FX_STALE_HOURS = int(os.getenv("FX_STALE_HOURS", "24"))
PRICING_BASE_CURRENCY = os.getenv("PRICING_BASE_CURRENCY", "usd").lower()

# Fallback if API unreachable (approximate market levels)
FALLBACK_RATES: dict[str, float] = {
    "ugx": 3800.0,
    "kes": 130.0,
    "rwf": 1300.0,
    "tzs": 2600.0,
    "zar": 18.5,
}

EA_CURRENCIES = ("ugx", "kes", "rwf", "tzs")


def fx_pricing_enabled() -> bool:
    return os.getenv("FX_PRICING_ENABLED", "true").lower() in ("true", "1", "yes")


def _fetch_from_api() -> tuple[dict[str, float], str, date | None]:
    req = urllib.request.Request(
        FX_API_URL,
        headers={"User-Agent": "EliteFintech/1.0 (billing-fx)"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode())

    if payload.get("result") != "success":
        raise ValueError(payload.get("error-type", "FX API error"))

    raw = payload.get("rates") or {}
    rates: dict[str, float] = {}
    for cur in EA_CURRENCIES:
        val = raw.get(cur.upper())
        if val is not None:
            rates[cur] = float(val)

    if is_south_africa_rate_needed():
        zar = raw.get("ZAR")
        if zar is not None:
            rates["zar"] = float(zar)

    if len(rates) < len(EA_CURRENCIES):
        missing = set(EA_CURRENCIES) - set(rates.keys())
        raise ValueError(f"FX API missing currencies: {missing}")

    trading_date = None
    updated_unix = payload.get("time_last_update_unix")
    if updated_unix:
        trading_date = datetime.fromtimestamp(updated_unix, tz=timezone.utc).date()

    source = FX_API_URL.split("/")[2] if "//" in FX_API_URL else "fx-api"
    return rates, source, trading_date


def is_south_africa_rate_needed() -> bool:
    from billing.services.regional import is_south_africa

    return is_south_africa()


@transaction.atomic
def refresh_market_rates(*, force: bool = False) -> FxRateSnapshot:
    """Fetch latest trading rates and persist snapshot."""
    if not force:
        latest = FxRateSnapshot.objects.order_by("-fetched_at").first()
        if latest and not latest.is_stale(FX_STALE_HOURS):
            return latest

    try:
        rates, source, trading_date = _fetch_from_api()
        source_label = f"{source} (live)"
    except (urllib.error.URLError, ValueError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("FX API fetch failed, using fallback rates: %s", exc)
        rates = dict(FALLBACK_RATES)
        source_label = "fallback (API unavailable)"
        trading_date = date.today()

    return FxRateSnapshot.objects.create(
        base_currency=PRICING_BASE_CURRENCY,
        rates=rates,
        source=source_label,
        trading_date=trading_date or date.today(),
    )


def ensure_fresh_rates() -> FxRateSnapshot | None:
    if not fx_pricing_enabled():
        return None
    latest = FxRateSnapshot.objects.order_by("-fetched_at").first()
    if latest is None or latest.is_stale(FX_STALE_HOURS):
        return refresh_market_rates()
    return latest


def get_latest_snapshot() -> FxRateSnapshot | None:
    if not fx_pricing_enabled():
        return None
    return ensure_fresh_rates()


def rate_for_currency(currency: str, snapshot: FxRateSnapshot | None = None) -> float:
    cur = currency.lower()
    snap = snapshot or get_latest_snapshot()
    if snap and cur in snap.rates:
        return float(snap.rates[cur])
    return FALLBACK_RATES.get(cur, 1.0)


def rates_public_payload(snapshot: FxRateSnapshot | None = None) -> dict:
    snap = snapshot or get_latest_snapshot()
    if not snap:
        return {
            "enabled": False,
            "pricing_mode": "static",
            "base_currency": PRICING_BASE_CURRENCY.upper(),
        }
    return {
        "enabled": True,
        "pricing_mode": "market_daily",
        "base_currency": snap.base_currency.upper(),
        "rates": {k.upper(): v for k, v in snap.rates.items()},
        "source": snap.source,
        "trading_date": snap.trading_date.isoformat() if snap.trading_date else None,
        "fetched_at": snap.fetched_at.isoformat(),
        "stale_after_hours": FX_STALE_HOURS,
        "next_refresh_hint": (
            snap.fetched_at + timedelta(hours=FX_STALE_HOURS)
        ).isoformat(),
    }
