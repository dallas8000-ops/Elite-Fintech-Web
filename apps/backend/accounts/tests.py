from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.cookies import REFRESH_COOKIE_NAME
from organizations.models import Membership, Organization, Role

REGISTER_PAYLOAD = {
    "email": "owner@elitefintech.co.ug",
    "password": "demo12345",
    "name": "Owner User",
    "organization_name": "Kampala Wallets",
    "country": "UG",
    "province": "CENTRAL",
    "industry_sector": "payments",
    "data_consent": True,
}


class AuthApiTests(APITestCase):
    def test_register_creates_owner_membership_and_sets_refresh_cookie(self):
        response = self.client.post("/api/v1/auth/register/", REGISTER_PAYLOAD, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("token", response.data)
        self.assertNotIn("refresh", response.data)
        self.assertIn(REFRESH_COOKIE_NAME, response.cookies)
        self.assertEqual(response.data["organization"]["country"], "UG")

        org = Organization.objects.get(name="Kampala Wallets")
        membership = Membership.objects.get(organization=org, user__email=REGISTER_PAYLOAD["email"])
        self.assertEqual(membership.role, Role.OWNER)

    def test_login_returns_membership_context_and_refresh_cookie(self):
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
        self.assertIn(REFRESH_COOKIE_NAME, response.cookies)
        self.assertNotIn("refresh", response.data)

    def test_refresh_issues_new_access_token(self):
        self.client.post("/api/v1/auth/register/", REGISTER_PAYLOAD, format="json")
        response = self.client.post("/api/v1/auth/refresh/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn(REFRESH_COOKIE_NAME, response.cookies)

    def test_logout_revokes_refresh_token(self):
        self.client.post("/api/v1/auth/register/", REGISTER_PAYLOAD, format="json")
        self.client.post("/api/v1/auth/logout/", format="json")
        response = self.client.post("/api/v1/auth/refresh/", format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


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

    def test_admin_can_update_organization_settings(self):
        user_model = get_user_model()
        admin = user_model.objects.create_user(
            email="admin2@elitefintech.co.ug",
            password="demo12345",
            name="Admin Two",
        )
        org = Organization.objects.create(
            name="Old Name",
            slug="old-name",
            country="UG",
            province="CENTRAL",
            industry_sector="Payments",
        )
        Membership.objects.create(user=admin, organization=org, role=Role.ADMIN)

        self.client.credentials(HTTP_AUTHORIZATION=self._auth_header_for(admin, org.id, Role.ADMIN))
        response = self.client.patch(
            "/api/v1/org/",
            {
                "name": "Kampala Pay Ltd",
                "vat_number": "1000999888",
                "industry_sector": "Payments & Wallets",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["organization"]["name"], "Kampala Pay Ltd")
        self.assertEqual(response.data["organization"]["vat_number"], "1000999888")
        org.refresh_from_db()
        self.assertEqual(org.name, "Kampala Pay Ltd")

    def test_viewer_cannot_update_organization_settings(self):
        user_model = get_user_model()
        viewer = user_model.objects.create_user(
            email="viewer2@elitefintech.co.ug",
            password="demo12345",
            name="Viewer Two",
        )
        org = Organization.objects.create(
            name="Locked Org",
            slug="locked-org",
            country="UG",
            province="CENTRAL",
        )
        Membership.objects.create(user=viewer, organization=org, role=Role.VIEWER)

        self.client.credentials(HTTP_AUTHORIZATION=self._auth_header_for(viewer, org.id, Role.VIEWER))
        response = self.client.patch(
            "/api/v1/org/",
            {"name": "Hacked Name"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
