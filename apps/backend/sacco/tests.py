from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from sacco.models import LedgerEntry, PaymentIntent, PaymentIntentStatus, SaccoMember
from sacco.services.intents import complete_intent_success, initiate_collection
from sacco.services.ledger import member_balance
from organizations.models import Membership, Organization, Role


class CollectionsApiTests(APITestCase):
    def _auth_header_for(self, user, org_id: str, role: str) -> str:
        refresh = RefreshToken.for_user(user)
        refresh["organization_id"] = str(org_id)
        refresh["role"] = role
        access = refresh.access_token
        access["organization_id"] = str(org_id)
        access["role"] = role
        return f"Bearer {access}"

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="treasurer@demo.sacco.ug",
            password="demo12345",
            name="Treasurer",
        )
        self.org = Organization.objects.create(
            name="Kampala Urban SACCO",
            slug="kampala-urban-sacco",
            country="UG",
            province="CENTRAL",
        )
        Membership.objects.create(user=self.user, organization=self.org, role=Role.ADMIN)
        self.member = SaccoMember.objects.create(
            organization=self.org,
            member_number="M001",
            full_name="Jane Nakato",
            phone="+256700000001",
            momo_network="MTN",
        )
        self.auth = self._auth_header_for(self.user, self.org.id, Role.ADMIN)

    def test_create_and_list_members(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth)
        response = self.client.post(
            "/api/v1/members/",
            {
                "member_number": "M002",
                "full_name": "John Okello",
                "phone": "+256700000002",
                "momo_network": "AIRTEL",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        listing = self.client.get("/api/v1/members/")
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(len(listing.data["members"]), 2)

    @patch.dict("os.environ", {"FLUTTERWAVE_SECRET_KEY": ""}, clear=False)
    def test_initiate_without_flutterwave_returns_503(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth)
        response = self.client.post(
            "/api/v1/collections/initiate/",
            {"member_id": str(self.member.id), "amount_minor": 50000, "purpose": "DUES"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("sacco.services.intents.get_flutterwave_adapter")
    @patch.dict("os.environ", {"FLUTTERWAVE_SECRET_KEY": "test-key"}, clear=False)
    def test_initiate_collection_creates_pending_intent(self, mock_adapter):
        from sacco.services.payments.base import ChargeResult

        mock_adapter.return_value.initiate_mobile_money.return_value = ChargeResult(
            provider_reference="efs_test",
            status="pending",
            message="Check phone",
            provider_transaction_id="12345",
            raw={"status": "success"},
        )
        self.client.credentials(HTTP_AUTHORIZATION=self.auth)
        response = self.client.post(
            "/api/v1/collections/initiate/",
            {"member_id": str(self.member.id), "amount_minor": 50000, "purpose": "DUES_2026_06"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], PaymentIntentStatus.PENDING)
        self.assertEqual(PaymentIntent.objects.count(), 1)

    def test_webhook_success_credits_ledger_once(self):
        intent = PaymentIntent.objects.create(
            idempotency_key="abc",
            organization=self.org,
            member=self.member,
            amount_minor=50000,
            provider_reference="efs_webhook_test",
            phone=self.member.phone,
            purpose="DUES",
            expires_at=timezone.now() + timedelta(minutes=15),
            status=PaymentIntentStatus.PENDING,
        )
        complete_intent_success(intent, provider_transaction_id="999", raw={"status": "successful"})
        self.assertEqual(LedgerEntry.objects.count(), 1)
        self.assertEqual(member_balance(self.member), 50000)

        complete_intent_success(intent, provider_transaction_id="999", raw={"status": "successful"})
        self.assertEqual(LedgerEntry.objects.count(), 1)

    def test_members_require_auth(self):
        response = self.client.get("/api/v1/members/")
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
