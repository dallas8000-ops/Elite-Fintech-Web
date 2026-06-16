from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from billing.models import PaymentEvent, Subscription
from billing.serializers import PaymentEventSerializer, SubscriptionSerializer


def org_group_name(organization_id: str) -> str:
    return f"org_{organization_id}"


def emit_to_org(organization_id: str, event_type: str, payload: dict) -> None:
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        org_group_name(organization_id),
        {"type": "billing.event", "event": event_type, "data": payload},
    )


def broadcast_payment_event(event: PaymentEvent) -> None:
    emit_to_org(
        str(event.organization_id),
        "payment:event",
        PaymentEventSerializer(event).data,
    )


def broadcast_subscription(subscription: Subscription) -> None:
    emit_to_org(
        str(subscription.organization_id),
        "subscription:updated",
        SubscriptionSerializer(subscription).data,
    )
