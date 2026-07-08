from datetime import datetime, timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from billing.models import PaymentProvider, Subscription, SubscriptionStatus
from billing.services.flutterwave_checkout import handle_subscription_webhook, tx_ref_for_subscription
from organizations.models import Membership, Organization, Role


class FlutterwaveCheckoutTests(APITestCase):
    def _auth_header_for(self, user, org_id: str, role: str) -> str:
        refresh = RefreshToken.for_user(user)
        refresh["organization_id"] = str(org_id)
        refresh["role"] = role
        access = refresh.access_token
        access["organization_id"] = str(org_id)
        access["role"] = role
        return f"Bearer {access}"

    @patch("billing.services.flutterwave_checkout.get_flutterwave_adapter")
    @patch.dict("os.environ", {"FLUTTERWAVE_SECRET_KEY": "test-key", "MARKET": "EA"}, clear=False)
    def test_checkout_calls_flutterwave_payments_api(self, mock_adapter):
        mock_adapter.return_value.create_hosted_checkout.return_value = {
            "link": "https://checkout.flutterwave.com/v3/hosted/pay/abc",
            "status": "success",
            "env": "sandbox",
        }
        user_model = get_user_model()
        user = user_model.objects.create_user(
            email="fw-admin@elitefintech.co.ug",
            password="demo12345",
            name="FW Admin",
        )
        org = Organization.objects.create(
            name="FW Org",
            slug="fw-org",
            country="UG",
            province="CENTRAL",
        )
        Membership.objects.create(user=user, organization=org, role=Role.ADMIN)

        self.client.credentials(HTTP_AUTHORIZATION=self._auth_header_for(user, org.id, Role.ADMIN))
        response = self.client.post(
            "/api/v1/billing/checkout/",
            {"tier": "STARTER", "rail": "MOBILE_MONEY"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["provider"], "FLUTTERWAVE")
        mock_adapter.return_value.create_hosted_checkout.assert_called_once()

    def test_subscription_webhook_activates_plan(self):
        org = Organization.objects.create(
            name="Webhook Org",
            slug="webhook-org",
            country="UG",
            province="CENTRAL",
        )
        tx_ref = tx_ref_for_subscription(org.id, "PRO", "nonce-1")
        handled = handle_subscription_webhook(
            {
                "tx_ref": tx_ref,
                "status": "successful",
                "amount": 550_000,
                "currency": "UGX",
                "id": 424242,
                "meta": {
                    "organization_id": str(org.id),
                    "tier": "PRO",
                    "rail": "MOBILE_MONEY",
                },
            },
            {},
        )
        self.assertTrue(handled)
        sub = Subscription.objects.get(organization=org)
        self.assertEqual(sub.plan_tier, "PRO")
        self.assertEqual(sub.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(sub.payment_provider, PaymentProvider.FLUTTERWAVE)
