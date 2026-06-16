from __future__ import annotations

from django.conf import settings

import stripe

_stripe_client: stripe.StripeClient | None = None


def get_stripe_client() -> stripe.StripeClient | None:
    global _stripe_client
    if not settings.STRIPE_SECRET_KEY:
        return None
    if _stripe_client is None:
        _stripe_client = stripe.StripeClient(settings.STRIPE_SECRET_KEY)
    return _stripe_client


def is_stripe_configured() -> bool:
    return bool(settings.STRIPE_SECRET_KEY)


STRIPE_PRICE_MAP = {
    settings.STRIPE_PRICE_STARTER: "STARTER",
    settings.STRIPE_PRICE_PRO: "PRO",
    settings.STRIPE_PRICE_ENTERPRISE: "ENTERPRISE",
}


def tier_from_price_id(price_id: str) -> str:
    return STRIPE_PRICE_MAP.get(price_id, "STARTER")


def construct_stripe_event(payload: bytes, sig_header: str):
    return stripe.Webhook.construct_event(
        payload=payload,
        sig_header=sig_header,
        secret=settings.STRIPE_WEBHOOK_SECRET,
    )
