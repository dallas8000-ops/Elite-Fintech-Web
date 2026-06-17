from __future__ import annotations

import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from billing.models import PaymentEventType, PaymentProvider, PaymentRail, SettlementStatus
from billing.services.events import broadcast_payment_event
from billing.services.regional import extract_vat_from_inclusive, vat_rate
from billing.webhooks import record_event
from sacco.models import (
    CollectionProvider,
    LedgerEntryType,
    PaymentIntent,
    PaymentIntentStatus,
)
from sacco.services.ledger import post_ledger_entry
from sacco.services.payments.flutterwave import get_flutterwave_adapter, is_flutterwave_configured


INTENT_TTL_MINUTES = 15


def tx_ref_for_intent(intent_id: uuid.UUID) -> str:
    return f"efs_{intent_id.hex}"


@transaction.atomic
def initiate_collection(
    *,
    organization,
    member,
    product,
    amount_minor: int,
    purpose: str,
    created_by,
    idempotency_key: str | None = None,
) -> PaymentIntent:
    if not is_flutterwave_configured():
        raise RuntimeError("Flutterwave not configured")

    key = idempotency_key or uuid.uuid4().hex
    existing = PaymentIntent.objects.filter(organization=organization, idempotency_key=key).first()
    if existing:
        return existing

    intent_id = uuid.uuid4()
    intent = PaymentIntent.objects.create(
        id=intent_id,
        idempotency_key=key,
        organization=organization,
        member=member,
        product=product,
        amount_minor=amount_minor,
        currency="ugx",
        rail=PaymentRail.MOBILE_MONEY,
        provider=CollectionProvider.FLUTTERWAVE,
        status=PaymentIntentStatus.INITIATED,
        provider_reference=tx_ref_for_intent(intent_id),
        phone=member.phone,
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=INTENT_TTL_MINUTES),
        created_by=created_by,
    )

    adapter = get_flutterwave_adapter()
    charge = adapter.initiate_mobile_money(
        phone=member.phone,
        amount_minor=amount_minor,
        currency="UGX",
        email=getattr(created_by, "email", "collections@elitefintech.co.ug"),
        tx_ref=intent.provider_reference,
        network=member.momo_network,
        meta={
            "organization_id": str(organization.id),
            "member_id": str(member.id),
            "intent_id": str(intent.id),
            "purpose": purpose,
        },
    )

    intent.status = PaymentIntentStatus.PENDING
    intent.metadata = {"charge": charge.raw or {}}
    if charge.provider_transaction_id:
        intent.provider_transaction_id = charge.provider_transaction_id
    intent.save(update_fields=["status", "metadata", "provider_transaction_id", "updated_at"])
    intent._charge_message = charge.message  # noqa: SLF001
    intent._payment_url = charge.payment_url  # noqa: SLF001
    return intent


def _vat_split(amount_minor: int, country: str) -> tuple[int, int]:
    rate = vat_rate(country)
    if rate <= 0:
        return amount_minor, 0
    ex_vat, vat = extract_vat_from_inclusive(amount_minor, country)
    return ex_vat, vat


@transaction.atomic
def complete_intent_success(intent: PaymentIntent, *, provider_transaction_id: str | None, raw: dict | None = None) -> PaymentIntent:
    if intent.status == PaymentIntentStatus.SUCCESS:
        return intent

    intent.status = PaymentIntentStatus.SUCCESS
    if provider_transaction_id:
        intent.provider_transaction_id = provider_transaction_id
    if raw:
        intent.metadata = {**intent.metadata, "webhook": raw}
    intent.save(update_fields=["status", "provider_transaction_id", "metadata", "updated_at"])

    post_ledger_entry(
        member=intent.member,
        entry_type=LedgerEntryType.CREDIT,
        amount_minor=intent.amount_minor,
        description=intent.purpose or "MoMo collection",
        payment_intent=intent,
        external_reference=provider_transaction_id or intent.provider_reference,
    )

    ex_vat, vat_amount = _vat_split(intent.amount_minor, intent.organization.country)
    external_id = f"flw_{provider_transaction_id or intent.provider_reference}"
    event = record_event(
        str(intent.organization_id),
        PaymentEventType.PAYMENT_SUCCEEDED,
        external_id,
        amount=ex_vat,
        vat_amount=vat_amount,
        provider=PaymentProvider.FLUTTERWAVE,
        rail=PaymentRail.MOBILE_MONEY,
        settlement_status=SettlementStatus.SETTLED,
        metadata={
            "payment_intent_id": str(intent.id),
            "member_id": str(intent.member_id),
            "member_number": intent.member.member_number,
            "purpose": intent.purpose,
            "provider_reference": intent.provider_reference,
        },
    )
    broadcast_payment_event(event)
    return intent


@transaction.atomic
def complete_intent_failed(intent: PaymentIntent, *, reason: str, raw: dict | None = None) -> PaymentIntent:
    if intent.status in (PaymentIntentStatus.SUCCESS, PaymentIntentStatus.FAILED):
        return intent

    intent.status = PaymentIntentStatus.FAILED
    if raw:
        intent.metadata = {**intent.metadata, "webhook": raw, "failure_reason": reason}
    else:
        intent.metadata = {**intent.metadata, "failure_reason": reason}
    intent.save(update_fields=["status", "metadata", "updated_at"])

    external_id = f"flw_fail_{intent.provider_reference}"
    event = record_event(
        str(intent.organization_id),
        PaymentEventType.PAYMENT_FAILED,
        external_id,
        amount=intent.amount_minor,
        provider=PaymentProvider.FLUTTERWAVE,
        rail=PaymentRail.MOBILE_MONEY,
        settlement_status=SettlementStatus.FAILED,
        metadata={
            "payment_intent_id": str(intent.id),
            "member_id": str(intent.member_id),
            "reason": reason,
        },
    )
    broadcast_payment_event(event)
    return intent


def expire_stale_intents() -> int:
    now = timezone.now()
    stale = PaymentIntent.objects.filter(status=PaymentIntentStatus.PENDING, expires_at__lt=now)
    count = stale.update(status=PaymentIntentStatus.EXPIRED, updated_at=now)
    return count


def maybe_verify_pending_intent(intent: PaymentIntent) -> PaymentIntent:
    if intent.status != PaymentIntentStatus.PENDING or not intent.provider_transaction_id:
        return intent
    if not is_flutterwave_configured():
        return intent

    adapter = get_flutterwave_adapter()
    result = adapter.verify_transaction(intent.provider_transaction_id)
    data = result.get("data") or {}
    flw_status = (data.get("status") or "").lower()
    if flw_status == "successful":
        return complete_intent_success(intent, provider_transaction_id=intent.provider_transaction_id, raw=result)
    if flw_status in ("failed", "cancelled"):
        return complete_intent_failed(intent, reason=flw_status, raw=result)
    return intent
