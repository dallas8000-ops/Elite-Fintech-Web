from rest_framework import serializers

from billing.models import PaymentEvent, Subscription


class SubscriptionSerializer(serializers.ModelSerializer):
    planTier = serializers.CharField(source="plan_tier")
    currentPeriodEnd = serializers.DateTimeField(source="current_period_end")
    cancelAtPeriodEnd = serializers.BooleanField(source="cancel_at_period_end")

    class Meta:
        model = Subscription
        fields = (
            "id",
            "planTier",
            "status",
            "amount_cents",
            "currency",
            "vat_cents",
            "currentPeriodEnd",
            "cancelAtPeriodEnd",
            "payment_provider",
        )


class PaymentEventSerializer(serializers.ModelSerializer):
    createdAt = serializers.DateTimeField(source="created_at")
    settlementStatus = serializers.CharField(source="settlement_status")

    class Meta:
        model = PaymentEvent
        fields = (
            "id",
            "type",
            "amount",
            "vat_amount",
            "currency",
            "payment_provider",
            "payment_rail",
            "settlementStatus",
            "createdAt",
            "metadata",
        )


class CheckoutSerializer(serializers.Serializer):
    tier = serializers.ChoiceField(choices=["STARTER", "PRO", "ENTERPRISE"])
    rail = serializers.ChoiceField(
        choices=[
            "INSTANT_EFT", "PAYSHAP", "DEBIT_ORDER", "EFT", "RNCS", "CARD",
        ],
        default="INSTANT_EFT",
    )
    provider = serializers.ChoiceField(
        choices=["PAYFAST", "STRIPE", "OZOW", "PEACH_PAYMENTS"],
        required=False,
        allow_null=True,
    )
