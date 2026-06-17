from datetime import datetime, timedelta, timezone
import logging
import time

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.utils import OperationalError
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView

from billing.models import (
    PaymentEvent,
    PaymentEventType,
    PaymentProvider,
    SettlementStatus,
    Subscription,
    SubscriptionStatus,
)
from billing.services.events import broadcast_payment_event, broadcast_subscription
from billing.services.payfast import map_payfast_method, verify_payfast_itn
from billing.services.regional import default_currency, extract_vat_from_inclusive, plan_by_tier
from billing.services.stripe_service import construct_stripe_event, get_stripe_client, tier_from_price_id

logger = logging.getLogger(__name__)


def race_safe_update_or_create_subscription(organization_id: str, defaults: dict) -> Subscription:
    """Race-safe subscription upsert for concurrent webhook deliveries."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with transaction.atomic():
                sub, _created = Subscription.objects.update_or_create(
                    organization_id=organization_id,
                    defaults=defaults,
                )
            return sub
        except IntegrityError:
            with transaction.atomic():
                sub = Subscription.objects.get(organization_id=organization_id)
                for field, value in defaults.items():
                    setattr(sub, field, value)
                sub.save(update_fields=list(defaults.keys()))
            return sub
        except OperationalError:
            if attempt < max_retries - 1:
                time.sleep(0.05 * (2**attempt))
                continue
            raise


def record_event(
    organization_id: str,
    event_type: str,
    external_id: str,
    *,
    amount: int | None = None,
    vat_amount: int | None = None,
    provider: str | None = None,
    rail: str | None = None,
    settlement_status: str = SettlementStatus.SETTLED,
    metadata: dict | None = None,
) -> PaymentEvent:
    """Idempotent on external_event_id — safe under concurrent webhook delivery."""
    try:
        with transaction.atomic():
            event, created = PaymentEvent.objects.get_or_create(
                external_event_id=external_id,
                defaults={
                    "organization_id": organization_id,
                    "type": event_type,
                    "amount": amount,
                    "vat_amount": vat_amount,
                    "currency": default_currency(),
                    "payment_provider": provider,
                    "payment_rail": rail,
                    "settlement_status": settlement_status,
                    "metadata": metadata or {},
                },
            )
    except IntegrityError:
        event = PaymentEvent.objects.get(external_event_id=external_id)
        created = False

    if created:
        broadcast_payment_event(event)
    return event


@method_decorator(csrf_exempt, name="dispatch")
class PayfastWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    @transaction.atomic
    def post(self, request):
        body = {k: v for k, v in request.POST.items()}
        if not verify_payfast_itn(body):
            return HttpResponse("Invalid signature", status=400)

        if body.get("payment_status") != "COMPLETE":
            organization_id = body.get("custom_str1")
            if body.get("payment_status") == "PENDING" and organization_id:
                record_event(
                    organization_id,
                    PaymentEventType.EFT_PENDING,
                    f"pf_pending_{body.get('m_payment_id')}",
                    amount=int(float(body.get("amount_gross", "0")) * 100),
                    provider=PaymentProvider.PAYFAST,
                    rail=body.get("custom_str4") or map_payfast_method(body.get("payment_method")),
                    settlement_status=SettlementStatus.PENDING,
                )
            return HttpResponse("OK")

        organization_id = body.get("custom_str1")
        plan_tier = body.get("custom_str2", "STARTER")
        if not organization_id:
            return HttpResponse("Missing org", status=400)

        plan = plan_by_tier(plan_tier) or plan_by_tier("STARTER")
        amount_cents = int(float(body.get("amount_gross", "0")) * 100)
        _, vat = extract_vat_from_inclusive(amount_cents)
        rail = body.get("custom_str4") or map_payfast_method(body.get("payment_method"))
        now = datetime.now(timezone.utc)

        sub = race_safe_update_or_create_subscription(
            organization_id,
            defaults={
                "external_subscription_id": body.get("pf_payment_id") or body.get("m_payment_id"),
                "payment_provider": PaymentProvider.PAYFAST,
                "plan_tier": plan_tier,
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
            f"pf_checkout_{body.get('pf_payment_id')}",
            amount=amount_cents,
            vat_amount=vat,
            provider=PaymentProvider.PAYFAST,
            rail=rail,
            metadata={"pf_payment_id": body.get("pf_payment_id")},
        )
        record_event(
            organization_id,
            PaymentEventType.INVOICE_PAID,
            f"pf_invoice_{body.get('pf_payment_id')}",
            amount=amount_cents,
            vat_amount=vat,
            provider=PaymentProvider.PAYFAST,
            rail=rail,
        )

        return HttpResponse("OK")


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    MAX_EVENT_AGE_SECONDS = 300

    @transaction.atomic
    def post(self, request):
        client = get_stripe_client()
        if not client or not settings.STRIPE_WEBHOOK_SECRET:
            return HttpResponse("Stripe not configured", status=400)

        sig = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        try:
            event = construct_stripe_event(request.body, sig)
        except Exception:
            return HttpResponse("Invalid signature", status=400)

        event_created = getattr(event, "created", None)
        if event_created is not None:
            age_seconds = datetime.now(timezone.utc).timestamp() - event_created
            if age_seconds > self.MAX_EVENT_AGE_SECONDS:
                logger.warning(
                    "Rejecting stale Stripe webhook event %s (age=%.0fs, type=%s)",
                    getattr(event, "id", "?"),
                    age_seconds,
                    event.type,
                )
                return HttpResponse("Event too old", status=400)

        obj = event.data.object
        metadata = dict(getattr(obj, "metadata", None) or {})
        org_id = metadata.get("organization_id")

        if event.type == "checkout.session.completed" and org_id:
            record_event(
                org_id,
                PaymentEventType.CHECKOUT_COMPLETED,
                f"stripe_checkout_{obj.id}",
                amount=getattr(obj, "amount_total", None),
                provider=PaymentProvider.STRIPE,
            )
        elif event.type == "invoice.paid" and org_id:
            record_event(
                org_id,
                PaymentEventType.INVOICE_PAID,
                f"stripe_invoice_{obj.id}",
                amount=getattr(obj, "amount_paid", None),
                provider=PaymentProvider.STRIPE,
            )
        elif event.type == "customer.subscription.updated" and org_id:
            items = obj.get("items", {}).get("data", []) if obj.get("items") else []
            price = items[0]["price"] if items else {}
            price_id = price.get("id", "")
            tier = tier_from_price_id(price_id)

            quantity = items[0].get("quantity", 1) if items else 1
            unit_amount = price.get("unit_amount")
            amount_cents = unit_amount * quantity if unit_amount is not None else None

            period_start_unix = obj.get("current_period_start")
            period_end_unix = obj.get("current_period_end")
            period_start = (
                datetime.fromtimestamp(period_start_unix, tz=timezone.utc)
                if period_start_unix
                else datetime.now(timezone.utc)
            )
            period_end = (
                datetime.fromtimestamp(period_end_unix, tz=timezone.utc)
                if period_end_unix
                else period_start + timedelta(days=30)
            )

            existing = Subscription.objects.filter(organization_id=org_id).first()
            defaults = {
                "external_subscription_id": obj.id,
                "external_price_id": price_id,
                "payment_provider": PaymentProvider.STRIPE,
                "plan_tier": tier or (existing.plan_tier if existing else "STARTER"),
                "status": obj.status.upper() if hasattr(obj, "status") else SubscriptionStatus.ACTIVE,
                "amount_cents": amount_cents if amount_cents is not None else (existing.amount_cents if existing else 0),
                "currency": (price.get("currency") or default_currency()).lower(),
                "current_period_start": period_start,
                "current_period_end": period_end,
                "cancel_at_period_end": bool(obj.get("cancel_at_period_end", False)),
            }
            if tier is None:
                logger.warning(
                    "Stripe subscription %s updated with unrecognized price_id=%r for org %s; "
                    "keeping existing plan_tier.",
                    obj.id,
                    price_id,
                    org_id,
                )

            sub = race_safe_update_or_create_subscription(org_id, defaults)
            broadcast_subscription(sub)

        return HttpResponse("OK")
