"""Webhook burn-in tests — idempotency, race safety, and stale-event rejection."""

from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.test import APITestCase

from billing.models import PaymentEvent, PaymentEventType, PaymentProvider, Subscription, SubscriptionStatus
from billing.webhooks import record_event, race_safe_update_or_create_subscription
from organizations.models import Organization


class RecordEventIdempotencyTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Webhook Org",
            slug="webhook-org",
            country="ZA",
            province="GP",
        )

    @patch("billing.webhooks.broadcast_payment_event")
    def test_duplicate_external_id_creates_one_row(self, mock_broadcast):
        record_event(
            str(self.org.id),
            PaymentEventType.CHECKOUT_COMPLETED,
            "evt_dup_1",
            amount=1200,
            provider=PaymentProvider.STRIPE,
        )
        record_event(
            str(self.org.id),
            PaymentEventType.CHECKOUT_COMPLETED,
            "evt_dup_1",
            amount=1200,
            provider=PaymentProvider.STRIPE,
        )
        self.assertEqual(PaymentEvent.objects.filter(external_event_id="evt_dup_1").count(), 1)
        mock_broadcast.assert_called_once()


class RaceSafeSubscriptionTests(TransactionTestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Race Org",
            slug="race-org",
            country="ZA",
            province="GP",
        )

    def test_concurrent_upserts_leave_one_subscription(self):
        defaults = {
            "external_subscription_id": "sub_race",
            "payment_provider": PaymentProvider.STRIPE,
            "plan_tier": "PRO",
            "status": SubscriptionStatus.ACTIVE,
            "amount_cents": 3500,
            "currency": "usd",
            "current_period_start": datetime.now(timezone.utc),
            "current_period_end": datetime.now(timezone.utc) + timedelta(days=30),
            "cancel_at_period_end": False,
        }

        def upsert():
            race_safe_update_or_create_subscription(str(self.org.id), defaults)

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: upsert(), range(4)))

        self.assertEqual(Subscription.objects.filter(organization_id=self.org.id).count(), 1)
        sub = Subscription.objects.get(organization_id=self.org.id)
        self.assertEqual(sub.plan_tier, "PRO")


@override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
class StripeWebhookBurnInTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Stripe Org",
            slug="stripe-org",
            country="UG",
            province="CENTRAL",
        )

    @patch("billing.webhooks.get_stripe_client")
    @patch("billing.webhooks.construct_stripe_event")
    def test_stale_event_rejected_with_400(self, mock_construct, mock_client):
        mock_client.return_value = object()
        now = datetime.now(timezone.utc)
        mock_construct.return_value = SimpleNamespace(
            id="evt_stale",
            type="checkout.session.completed",
            created=(now - timedelta(minutes=10)).timestamp(),
            data=SimpleNamespace(
                object=SimpleNamespace(
                    id="cs_test",
                    metadata={"organization_id": str(self.org.id)},
                    amount_total=1200,
                )
            ),
        )

        response = self.client.post(
            "/webhooks/stripe/",
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b"Event too old")
        self.assertEqual(PaymentEvent.objects.count(), 0)

    @patch("billing.webhooks.broadcast_subscription")
    @patch("billing.webhooks.get_stripe_client")
    @patch("billing.webhooks.construct_stripe_event")
    @patch("billing.webhooks.tier_from_price_id", return_value=None)
    def test_unknown_price_keeps_existing_plan_tier(self, _mock_tier, mock_construct, mock_client, _mock_broadcast):
        mock_client.return_value = object()
        Subscription.objects.create(
            organization=self.org,
            external_subscription_id="sub_existing",
            payment_provider=PaymentProvider.STRIPE,
            plan_tier="ENTERPRISE",
            status=SubscriptionStatus.ACTIVE,
            amount_cents=12000,
            currency="usd",
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        )
        period_start = int(datetime.now(timezone.utc).timestamp())
        period_end = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
        mock_construct.return_value = SimpleNamespace(
            id="evt_sub_update",
            type="customer.subscription.updated",
            created=datetime.now(timezone.utc).timestamp(),
            data=SimpleNamespace(
                object={
                    "id": "sub_new",
                    "status": "active",
                    "cancel_at_period_end": False,
                    "current_period_start": period_start,
                    "current_period_end": period_end,
                    "items": {"data": [{"quantity": 1, "price": {"id": "price_unknown", "unit_amount": 3500, "currency": "usd"}}]},
                    "metadata": {"organization_id": str(self.org.id)},
                }
            ),
        )

        response = self.client.post(
            "/webhooks/stripe/",
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        self.assertEqual(response.status_code, 200)
        sub = Subscription.objects.get(organization_id=self.org.id)
        self.assertEqual(sub.plan_tier, "ENTERPRISE")


class PayfastWebhookBurnInTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="PayFast Org",
            slug="payfast-org",
            country="ZA",
            province="GP",
        )

    @patch("billing.webhooks.verify_payfast_itn", return_value=True)
    @patch("billing.webhooks.broadcast_subscription")
    @patch("billing.webhooks.broadcast_payment_event")
    def test_complete_payment_is_idempotent(self, _mock_event, _mock_sub, _mock_verify):
        body = {
            "payment_status": "COMPLETE",
            "custom_str1": str(self.org.id),
            "custom_str2": "PRO",
            "amount_gross": "350.00",
            "pf_payment_id": "pf_burnin_1",
            "m_payment_id": "pf_burnin_1",
            "payment_method": "cc",
        }
        for _ in range(2):
            response = self.client.post("/webhooks/payfast/", body)
            self.assertEqual(response.status_code, 200)

        self.assertEqual(Subscription.objects.filter(organization_id=self.org.id).count(), 1)
        self.assertEqual(PaymentEvent.objects.filter(organization_id=self.org.id).count(), 2)

    @patch("billing.webhooks.verify_payfast_itn", return_value=True)
    @patch("billing.webhooks.broadcast_payment_event")
    def test_pending_eft_records_pending_event_once(self, mock_broadcast, _mock_verify):
        body = {
            "payment_status": "PENDING",
            "custom_str1": str(self.org.id),
            "amount_gross": "120.00",
            "m_payment_id": "pf_pending_1",
            "payment_method": "eft",
        }
        self.client.post("/webhooks/payfast/", body)
        self.client.post("/webhooks/payfast/", body)

        self.assertEqual(
            PaymentEvent.objects.filter(
                external_event_id="pf_pending_pf_pending_1",
                type=PaymentEventType.EFT_PENDING,
            ).count(),
            1,
        )
        mock_broadcast.assert_called_once()
