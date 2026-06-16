from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from billing.models import FxRateSnapshot
from billing.services.market_pricing import plans_for_country_market, usd_to_minor
from organizations.models import Membership, Organization, Role


class MarketPricingTests(TestCase):
    def setUp(self):
        FxRateSnapshot.objects.create(
            base_currency="usd",
            rates={"ugx": 3800, "kes": 130, "rwf": 1300, "tzs": 2600},
            source="test-fixture",
            trading_date=date.today(),
        )

    def test_usd_to_minor_rounds_kes_to_cents(self):
        # 12 USD * 130 = 1560 KES -> rounded in major, returned as minor (cents)
        amount = usd_to_minor(12, "kes", rate=130)
        self.assertEqual(amount, 155000)

    def test_plans_for_country_market_returns_ea_tiers_with_fx_metadata(self):
        plans, meta = plans_for_country_market("UG")

        self.assertEqual(len(plans), 3)
        self.assertEqual({p["tier"] for p in plans}, {"STARTER", "PRO", "ENTERPRISE"})
        self.assertEqual(meta["country"], "UG")
        self.assertEqual(meta["currency"], "ugx")
        self.assertEqual(meta["fx_rate"], 3800.0)
        self.assertIn("trading_date", meta)

    def test_invalid_country_falls_back_to_default_country(self):
        plans, meta = plans_for_country_market("XX")

        self.assertEqual(len(plans), 3)
        self.assertEqual(meta["country"], "UG")


class EastAfricaCheckoutPathTests(APITestCase):
    def _auth_header_for(self, user, org_id: str, role: str) -> str:
        refresh = RefreshToken.for_user(user)
        refresh["organization_id"] = str(org_id)
        refresh["role"] = role
        access = refresh.access_token
        access["organization_id"] = str(org_id)
        access["role"] = role
        return f"Bearer {access}"

    @patch.dict("os.environ", {"FLUTTERWAVE_SECRET_KEY": ""}, clear=False)
    def test_instant_eft_routes_to_flutterwave_path(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            email="momo-admin@elitefintech.co.ug",
            password="demo12345",
            name="MoMo Admin",
        )
        org = Organization.objects.create(
            name="MoMo Smoke Org",
            slug="momo-smoke-org",
            country="UG",
            province="CENTRAL",
        )
        Membership.objects.create(user=user, organization=org, role=Role.ADMIN)

        self.client.credentials(HTTP_AUTHORIZATION=self._auth_header_for(user, org.id, Role.ADMIN))
        response = self.client.post(
            "/api/v1/billing/checkout/",
            {"tier": "PRO", "rail": "INSTANT_EFT"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["provider"], "FLUTTERWAVE")
        self.assertIn("Flutterwave not configured", response.data["error"])
