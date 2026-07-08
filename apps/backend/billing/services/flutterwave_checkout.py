"""Flutterwave hosted checkout for East Africa subscription billing."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone

from django.conf import settings

from billing.models import PaymentEventType, PaymentProvider, SubscriptionStatus
from billing.services.regional import default_currency, extract_vat_from_inclusive, plan_by_tier
from billing.services.events import broadcast_subscription
from billing.webhooks import race_safe_update_or_create_subscription, record_event
from sacco.services.payments.flutterwave import get_flutterwave_adapter, is_flutterwave_configured

logger = logging.getLogger(__name__)

BILLING_TX_REF_PREFIX = "efssub"


def tx_ref_for_subscription(org_id: uuid.UUID, tier: str, nonce: str) -> str:
    digest = hashlib.sha256(f"{org_id}:{tier}:{nonce}".encode()).hexdigest()[:24]
    return f"efssub{digest}"


def create_flutterwave_subscription_checkout(
    *,
    organization,
    tier: str,
    rail: str,
    email: str,
    plan: dict,
    client_nonce: str | None = None,
) -> dict:
    if not is_flutterwave_configured():
        raise RuntimeError("Flutterwave not configured")

    currency = default_currency(organization.country).upper()
    amount = plan["amount_cents"]
    success_url = f"{settings.CLIENT_URL}/dashboard?checkout=success&rail={rail}&provider=FLUTTERWAVE"

    adapter = get_flutterwave_adapter()
    last_error: RuntimeError | None = None
    for attempt in range(3):
        nonce = client_nonce if attempt == 0 and client_nonce else uuid.uuid4().hex
        tx_ref = tx_ref_for_subscription(organization.id, tier, nonce)
        try:
            result = adapter.create_hosted_checkout(
                tx_ref=tx_ref,
                amount=amount,
                currency=currency,
                email=email,
                customer_name=organization.name,
                title="Elite Fintech Systems",
                description=f"{plan['label']} plan — {organization.name}",
                redirect_url=success_url,
                rail=rail,
                country=organization.country,
                meta={
                    "organization_id": str(organization.id),
                    "tier": tier,
                    "rail": rail,
                    "checkout_type": "subscription",
                },
            )
        except RuntimeError as exc:
            last_error = exc
            if "already exists" in str(exc).lower() and attempt < 2:
                client_nonce = None
                continue
            raise

        link = result.get("link")
        if not link:
            message = result.get("message") or "Flutterwave checkout unavailable"
            raise RuntimeError(message)

        return {
            "url": link,
            "provider": "FLUTTERWAVE",
            "rail": rail,
            "tx_ref": tx_ref,
            "env": result.get("env", "sandbox"),
        }

    if last_error:
        raise last_error
    raise RuntimeError("Flutterwave checkout unavailable")


def handle_subscription_webhook(data: dict, payload: dict) -> bool:
    """Activate subscription when Flutterwave confirms a billing checkout payment."""
    tx_ref = data.get("tx_ref") or data.get("txRef") or data.get("reference") or ""
    if not tx_ref.startswith(BILLING_TX_REF_PREFIX):
        return False

    meta = data.get("meta") or {}
    organization_id = meta.get("organization_id")
    tier = meta.get("tier") or "STARTER"
    rail = meta.get("rail") or "MOBILE_MONEY"

    if not organization_id and tx_ref.startswith(BILLING_TX_REF_PREFIX):
        meta_org = meta.get("organization_id")
        if meta_org:
            organization_id = meta_org

    if not organization_id:
        logger.warning("Flutterwave billing webhook: missing organization_id for %s", tx_ref)
        return True

    status_value = (data.get("status") or "").lower()
    if status_value not in ("successful", "success", "succeeded"):
        logger.info("Flutterwave billing webhook ignored status %s for %s", status_value, tx_ref)
        return True

    plan = plan_by_tier(tier) or plan_by_tier("STARTER")
    amount_cents = int(data.get("amount") or (plan["amount_cents"] if plan else 0))
    _, vat = extract_vat_from_inclusive(amount_cents)
    flw_id = str(data.get("id") or data.get("transaction_id") or tx_ref)
    now = datetime.now(timezone.utc)

    sub = race_safe_update_or_create_subscription(
        organization_id,
        defaults={
            "external_subscription_id": flw_id,
            "payment_provider": PaymentProvider.FLUTTERWAVE,
            "plan_tier": tier,
            "status": SubscriptionStatus.ACTIVE,
            "amount_cents": plan["amount_cents"] if plan else amount_cents,
            "currency": default_currency(),
            "vat_cents": vat,
            "current_period_start": now,
            "current_period_end": now + timedelta(days=30),
            "cancel_at_period_end": False,
        },
    )
    broadcast_subscription(sub)

    record_event(
        organization_id,
        PaymentEventType.CHECKOUT_COMPLETED,
        f"fw_checkout_{flw_id}",
        amount=amount_cents,
        vat_amount=vat,
        provider=PaymentProvider.FLUTTERWAVE,
        rail=rail,
        metadata={"tx_ref": tx_ref, "flutterwave_id": flw_id},
    )
    record_event(
        organization_id,
        PaymentEventType.INVOICE_PAID,
        f"fw_invoice_{flw_id}",
        amount=amount_cents,
        vat_amount=vat,
        provider=PaymentProvider.FLUTTERWAVE,
        rail=rail,
    )
    return True
