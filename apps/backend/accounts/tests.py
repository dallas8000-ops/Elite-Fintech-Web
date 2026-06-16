from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from organizations.models import Membership, Organization, Role


class AuthApiTests(APITestCase):
    def test_register_creates_owner_membership_and_returns_tokens(self):
        payload = {
            "email": "owner@elitefintech.co.ug",
            "password": "demo12345",
            "name": "Owner User",
            "organization_name": "Kampala Wallets",
            "country": "UG",
            "province": "CENTRAL",
            "industry_sector": "payments",
            "data_consent": True,
        }
        response = self.client.post("/api/v1/auth/register/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["organization"]["country"], "UG")

        org = Organization.objects.get(name="Kampala Wallets")
        membership = Membership.objects.get(organization=org, user__email=payload["email"])
        self.assertEqual(membership.role, Role.OWNER)

    def test_login_returns_membership_context(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            email="member@elitefintech.co.ke",
            password="demo12345",
            name="Member User",
        )
        org = Organization.objects.create(
            name="Nairobi Pay",
            slug="nairobi-pay",
            country="KE",
            province="NAIROBI",
        )
        Membership.objects.create(user=user, organization=org, role=Role.ADMIN)

        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "member@elitefintech.co.ke", "password": "demo12345"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], Role.ADMIN)
        self.assertEqual(response.data["organization"]["id"], str(org.id))
        self.assertGreaterEqual(len(response.data["organizations"]), 1)


class OrganizationRbacTests(APITestCase):
    def _auth_header_for(self, user, org_id: str, role: str) -> str:
        refresh = RefreshToken.for_user(user)
        refresh["organization_id"] = str(org_id)
        refresh["role"] = role
        access = refresh.access_token
        access["organization_id"] = str(org_id)
        access["role"] = role
        return f"Bearer {access}"

    def test_viewer_cannot_invite_members(self):
        user_model = get_user_model()
        viewer = user_model.objects.create_user(
            email="viewer@elitefintech.co.ug",
            password="demo12345",
            name="Viewer User",
        )
        org = Organization.objects.create(
            name="Lake Payments",
            slug="lake-payments",
            country="UG",
            province="CENTRAL",
        )
        Membership.objects.create(user=viewer, organization=org, role=Role.VIEWER)

        self.client.credentials(HTTP_AUTHORIZATION=self._auth_header_for(viewer, org.id, Role.VIEWER))
        response = self.client.post(
            "/api/v1/org/members/invite/",
            {
                "email": "new@elitefintech.co.ug",
                "name": "New User",
                "password": "demo12345",
                "role": Role.MEMBER,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_invite_members(self):
        user_model = get_user_model()
        admin = user_model.objects.create_user(
            email="admin@elitefintech.co.ug",
            password="demo12345",
            name="Admin User",
        )
        org = Organization.objects.create(
            name="Kampala Switch",
            slug="kampala-switch",
            country="UG",
            province="CENTRAL",
        )
        Membership.objects.create(user=admin, organization=org, role=Role.ADMIN)

        self.client.credentials(HTTP_AUTHORIZATION=self._auth_header_for(admin, org.id, Role.ADMIN))
        response = self.client.post(
            "/api/v1/org/members/invite/",
            {
                "email": "member2@elitefintech.co.ug",
                "name": "Member Two",
                "password": "demo12345",
                "role": Role.MEMBER,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["member"]["role"], Role.MEMBER)
