"""
API contract self-checks — fast guards that catch regressions and miswired endpoints.

Run via: npm run check  (discovered as test_contracts.py)
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from organizations.models import Membership, Organization, Role


class ApiContractSelfCheckTests(APITestCase):
    """Verify critical paths return correct status codes, not 500s."""

    def test_health_endpoint_ok(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_login_returns_401(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "nobody@elitefintech.co.ug", "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("error", response.data)

    def test_protected_billing_stats_requires_auth(self):
        response = self.client.get("/api/v1/billing/stats/")
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_org_settings_requires_auth(self):
        response = self.client.get("/api/v1/org/")
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class FlutterwaveContractSelfCheckTests(APITestCase):
    """East Africa checkout must fail predictably until Flutterwave is fully integrated."""

    def _auth_header_for(self, user, org_id: str, role: str) -> str:
        refresh = RefreshToken.for_user(user)
        refresh["organization_id"] = str(org_id)
        refresh["role"] = role
        access = refresh.access_token
        access["organization_id"] = str(org_id)
        access["role"] = role
        return f"Bearer {access}"

    @patch.dict("os.environ", {"FLUTTERWAVE_SECRET_KEY": "test-secret-key", "MARKET": "EA"}, clear=False)
    def test_flutterwave_checkout_returns_501_not_500(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            email="contract@elitefintech.co.ug",
            password="demo12345",
            name="Contract Check",
        )
        org = Organization.objects.create(
            name="Contract Org",
            slug="contract-org",
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

        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)
        self.assertEqual(response.data.get("provider"), "FLUTTERWAVE")
        self.assertIn("pending", response.data.get("error", "").lower())

    @patch.dict("os.environ", {"FLUTTERWAVE_SECRET_KEY": "", "MARKET": "EA"}, clear=False)
    def test_flutterwave_missing_config_returns_503(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            email="contract2@elitefintech.co.ug",
            password="demo12345",
            name="Contract Check Two",
        )
        org = Organization.objects.create(
            name="Contract Org Two",
            slug="contract-org-two",
            country="UG",
            province="CENTRAL",
        )
        Membership.objects.create(user=user, organization=org, role=Role.ADMIN)

        self.client.credentials(HTTP_AUTHORIZATION=self._auth_header_for(user, org.id, Role.ADMIN))
        response = self.client.post(
            "/api/v1/billing/checkout/",
            {"tier": "STARTER", "rail": "INSTANT_EFT"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data.get("provider"), "FLUTTERWAVE")
