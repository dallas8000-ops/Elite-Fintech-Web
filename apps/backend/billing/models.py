import uuid

from django.db import models


class PlanTier(models.TextChoices):
    STARTER = "STARTER", "Starter"
    PRO = "PRO", "Pro"
    ENTERPRISE = "ENTERPRISE", "Enterprise"


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    TRIALING = "TRIALING", "Trialing"
    PAST_DUE = "PAST_DUE", "Past Due"
    CANCELED = "CANCELED", "Canceled"
    INCOMPLETE = "INCOMPLETE", "Incomplete"
    UNPAID = "UNPAID", "Unpaid"


class PaymentProvider(models.TextChoices):
    STRIPE = "STRIPE", "Stripe"
    PAYFAST = "PAYFAST", "PayFast"
    OZOW = "OZOW", "Ozow"
    PEACH_PAYMENTS = "PEACH_PAYMENTS", "Peach Payments"
    FLUTTERWAVE = "FLUTTERWAVE", "Flutterwave"
    PESAPAL = "PESAPAL", "Pesapal"


class PaymentRail(models.TextChoices):
    CARD = "CARD", "Card"
    EFT = "EFT", "EFT"
    INSTANT_EFT = "INSTANT_EFT", "Instant EFT"
    DEBIT_ORDER = "DEBIT_ORDER", "Debit Order"
    PAYSHAP = "PAYSHAP", "PayShap"
    RNCS = "RNCS", "Capitec Pay / RNCS"
    MOBILE_MONEY = "MOBILE_MONEY", "Mobile Money"
    USSD = "USSD", "USSD"
    AGENT_CASH = "AGENT_CASH", "Agent Cash"


class SettlementStatus(models.TextChoices):
    """African payments are often async — funds != authorised immediately."""
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    SETTLED = "SETTLED", "Settled"
    FAILED = "FAILED", "Failed"
    REVERSED = "REVERSED", "Reversed"


class PaymentEventType(models.TextChoices):
    SUBSCRIPTION_CREATED = "SUBSCRIPTION_CREATED", "Subscription Created"
    SUBSCRIPTION_UPDATED = "SUBSCRIPTION_UPDATED", "Subscription Updated"
    SUBSCRIPTION_CANCELED = "SUBSCRIPTION_CANCELED", "Subscription Canceled"
    INVOICE_PAID = "INVOICE_PAID", "Invoice Paid"
    INVOICE_FAILED = "INVOICE_FAILED", "Invoice Failed"
    PAYMENT_SUCCEEDED = "PAYMENT_SUCCEEDED", "Payment Succeeded"
    PAYMENT_FAILED = "PAYMENT_FAILED", "Payment Failed"
    CHECKOUT_COMPLETED = "CHECKOUT_COMPLETED", "Checkout Completed"
    EFT_PENDING = "EFT_PENDING", "EFT Pending"
    PAYSHAP_RECEIVED = "PAYSHAP_RECEIVED", "PayShap Received"


class FxRateSnapshot(models.Model):
    """Daily FX rates for market-based East Africa pricing."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    base_currency = models.CharField(max_length=3, default="usd")
    rates = models.JSONField(default=dict)
    source = models.CharField(max_length=128)
    trading_date = models.DateField()
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fx_rate_snapshots"
        ordering = ["-fetched_at"]

    def is_stale(self, max_hours: int = 24) -> bool:
        from datetime import timedelta

        from django.utils import timezone

        return self.fetched_at < timezone.now() - timedelta(hours=max_hours)


class Subscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        "organizations.Organization", on_delete=models.CASCADE, related_name="subscription"
    )
    external_subscription_id = models.CharField(max_length=128, unique=True)
    external_price_id = models.CharField(max_length=128, blank=True, null=True)
    payment_provider = models.CharField(
        max_length=32, choices=PaymentProvider.choices, default=PaymentProvider.PAYFAST
    )
    plan_tier = models.CharField(max_length=16, choices=PlanTier.choices)
    status = models.CharField(max_length=16, choices=SubscriptionStatus.choices)
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="ugx")
    vat_cents = models.PositiveIntegerField(default=0)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    cancel_at_period_end = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscriptions"


class PaymentEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="payment_events"
    )
    type = models.CharField(max_length=32, choices=PaymentEventType.choices)
    amount = models.PositiveIntegerField(blank=True, null=True)
    vat_amount = models.PositiveIntegerField(blank=True, null=True)
    currency = models.CharField(max_length=3, default="ugx")
    payment_provider = models.CharField(max_length=32, choices=PaymentProvider.choices, blank=True, null=True)
    payment_rail = models.CharField(max_length=32, choices=PaymentRail.choices, blank=True, null=True)
    settlement_status = models.CharField(
        max_length=16,
        choices=SettlementStatus.choices,
        default=SettlementStatus.SETTLED,
    )
    external_event_id = models.CharField(max_length=128, unique=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payment_events"
        ordering = ["-created_at"]
