from __future__ import annotations

import hashlib
from urllib.parse import urlencode

from django.conf import settings

from billing.services.sa_constants import SA_PLANS, SaPlanDict


def is_payfast_configured() -> bool:
    return bool(settings.PAYFAST_MERCHANT_ID and settings.PAYFAST_MERCHANT_KEY)


def _build_signature(data: dict[str, str], passphrase: str | None = None) -> str:
    sorted_keys = sorted(k for k in data if data[k] != "" and k != "signature")
    param_string = "&".join(
        f"{k}={data[k].replace(' ', '+')}" for k in sorted_keys
    )
    if passphrase:
        param_string += f"&passphrase={passphrase.replace(' ', '+')}"
    return hashlib.md5(param_string.encode()).hexdigest()


def create_payfast_checkout_url(
    *,
    organization_id: str,
    plan: SaPlanDict,
    customer_email: str,
    customer_name: str,
    return_url: str,
    cancel_url: str,
    notify_url: str,
    rail: str = "INSTANT_EFT",
) -> tuple[str, str]:
    if not is_payfast_configured():
        raise ValueError("PayFast is not configured")

    payment_id = f"pf_{organization_id}_{plan['tier']}_{rail}"
    amount = f"{plan['amount_cents'] / 100:.2f}"
    parts = customer_name.split(" ", 1)

    data: dict[str, str] = {
        "merchant_id": settings.PAYFAST_MERCHANT_ID,
        "merchant_key": settings.PAYFAST_MERCHANT_KEY,
        "return_url": return_url,
        "cancel_url": cancel_url,
        "notify_url": notify_url,
        "m_payment_id": payment_id,
        "amount": amount,
        "item_name": f"Elite Fintech — {plan['label']} Plan",
        "item_description": plan["description"],
        "email_address": customer_email,
        "name_first": parts[0],
        "name_last": parts[1] if len(parts) > 1 else "User",
        "subscription_type": "1",
        "recurring_amount": amount,
        "frequency": "3",
        "cycles": "0",
        "custom_str1": organization_id,
        "custom_str2": plan["tier"],
        "custom_str3": "zar",
        "custom_str4": rail,
    }

    data["signature"] = _build_signature(data, settings.PAYFAST_PASSPHRASE or None)

    base = (
        "https://sandbox.payfast.co.za/eng/process"
        if settings.PAYFAST_SANDBOX
        else "https://www.payfast.co.za/eng/process"
    )
    return f"{base}?{urlencode(data)}", payment_id


def verify_payfast_itn(body: dict[str, str]) -> bool:
    received = body.get("signature")
    if not received:
        return False
    computed = _build_signature(body, settings.PAYFAST_PASSPHRASE or None)
    return computed == received


def map_payfast_method(method: str | None) -> str:
    mapping = {"cc": "CARD", "eft": "EFT", "dc": "DEBIT_ORDER"}
    return mapping.get((method or "").lower(), "INSTANT_EFT")
