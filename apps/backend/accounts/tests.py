from unittest.mock import patch

from accounts.cookies import REFRESH_COOKIE_NAME
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.views import LoginView, RefreshView
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
    def test_register_creates_owner_membership_and_returns_tokens(self):
        response = self.client.post("/api/v1/auth/register/", REGISTER_PAYLOAD, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        self.assertIn(REFRESH_COOKIE_NAME, response.cookies)
        self.assertTrue(response.cookies[REFRESH_COOKIE_NAME]["httponly"])
        self.assertEqual(response.data["organization"]["country"], "UG")

        org = Organization.objects.get(name="Kampala Wallets")
        membership = Membership.objects.get(organization=org, user__email=REGISTER_PAYLOAD["email"])
        self.assertEqual(membership.role, Role.OWNER)

    def test_register_race_on_duplicate_email_returns_409_not_500(self):
        from django.db import IntegrityError

        payload = {**REGISTER_PAYLOAD, "email": "race-duplicate@elitefintech.co.ug", "organization_name": "Race Org"}

        with patch("accounts.views.User.objects.filter") as mock_filter, patch(
            "accounts.views.User.objects.create_user", side_effect=IntegrityError("unique constraint")
        ):
            mock_filter.return_value.exists.return_value = False
            response = self.client.post("/api/v1/auth/register/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("error", response.data)

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
        self.assertIn(REFRESH_COOKIE_NAME, response.cookies)


class TokenRefreshFlowTests(APITestCase):
    def setUp(self):
        cache.clear()

    def _register(self, email="refresh-owner@elitefintech.co.ug"):
        payload = {
            "email": email,
            "password": "demo12345",
            "name": "Refresh Owner",
            "organization_name": "Refresh Org",
            "country": "UG",
            "province": "CENTRAL",
            "data_consent": True,
        }
        return self.client.post("/api/v1/auth/register/", payload, format="json")

    def test_refresh_without_cookie_returns_401(self):
        response = self.client.post("/api/v1/auth/refresh/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_with_valid_cookie_issues_new_access_token(self):
        self._register()
        response = self.client.post("/api/v1/auth/refresh/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertNotIn("refresh", response.data)

    def test_refresh_after_membership_removed_is_rejected(self):
        register_response = self._register(email="soon-removed@elitefintech.co.ug")
        org_id = register_response.data["organization"]["id"]

        user_model = get_user_model()
        user = user_model.objects.get(email="soon-removed@elitefintech.co.ug")
        Membership.objects.filter(user=user, organization_id=org_id).delete()

        response = self.client.post("/api/v1/auth/refresh/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_refresh_reflects_role_change_since_last_login(self):
        register_response = self._register(email="role-change@elitefintech.co.ug")
        org_id = register_response.data["organization"]["id"]

        user_model = get_user_model()
        user = user_model.objects.get(email="role-change@elitefintech.co.ug")
        membership = Membership.objects.get(user=user, organization_id=org_id)
        membership.role = Role.VIEWER
        membership.save(update_fields=["role"])

        response = self.client.post("/api/v1/auth/refresh/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], Role.VIEWER)

    def test_logout_clears_refresh_cookie(self):
        self._register(email="logout-user@elitefintech.co.ug")
        response = self.client.post("/api/v1/auth/logout/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        refresh_response = self.client.post("/api/v1/auth/refresh/")
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_captured_refresh_token_is_rejected_after_logout_even_if_replayed(self):
        self._register(email="captured-token@elitefintech.co.ug")
        captured_refresh_value = self.client.cookies[REFRESH_COOKIE_NAME].value

        logout_response = self.client.post("/api/v1/auth/logout/")
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)

        self.client.cookies[REFRESH_COOKIE_NAME] = captured_refresh_value
        replay_response = self.client.post("/api/v1/auth/refresh/")
        self.assertEqual(replay_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rotated_token_reuse_within_grace_window_gets_access_only_no_new_refresh(self):
        self._register(email="rotation-grace-test@elitefintech.co.ug")
        captured_before_rotation = self.client.cookies[REFRESH_COOKIE_NAME].value

        first_refresh = self.client.post("/api/v1/auth/refresh/")
        self.assertEqual(first_refresh.status_code, status.HTTP_200_OK)

        self.client.cookies[REFRESH_COOKIE_NAME] = captured_before_rotation
        second_refresh = self.client.post("/api/v1/auth/refresh/")

        self.assertEqual(second_refresh.status_code, status.HTTP_200_OK)
        self.assertIn("access", second_refresh.data)
        self.assertNotIn("refresh", second_refresh.data)

    def test_rotated_token_reuse_outside_grace_window_is_rejected(self):
        from datetime import timedelta

        from django.utils import timezone

        self._register(email="rotation-stale-replay@elitefintech.co.ug")
        captured_before_rotation = self.client.cookies[REFRESH_COOKIE_NAME].value

        first_refresh = self.client.post("/api/v1/auth/refresh/")
        self.assertEqual(first_refresh.status_code, status.HTTP_200_OK)

        future_time = timezone.now() + timedelta(seconds=RefreshView.ROTATION_GRACE_SECONDS + 5)
        with patch("django.utils.timezone.now", return_value=future_time):
            self.client.cookies[REFRESH_COOKIE_NAME] = captured_before_rotation
            replay_outside_window = self.client.post("/api/v1/auth/refresh/")

        self.assertEqual(replay_outside_window.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_login_is_throttled_after_configured_limit(self):
        from django.conf import settings
        from django.test import Client

        configured_rate = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["auth-login"]
        limit = int(configured_rate.split("/")[0])

        client = Client(HTTP_HOST="testserver")
        responses = [
            client.post(
                "/api/v1/auth/login/",
                {"email": "nobody@elitefintech.co.ug", "password": "wrong"},
                content_type="application/json",
            )
            for _ in range(limit + 1)
        ]

        statuses = [r.status_code for r in responses]
        self.assertEqual(statuses[:limit], [status.HTTP_401_UNAUTHORIZED] * limit)
        self.assertEqual(statuses[limit], status.HTTP_429_TOO_MANY_REQUESTS)

    def test_throttle_rate_is_actually_wired_to_the_view(self):
        throttle = ScopedRateThrottle()
        self.assertEqual(LoginView.throttle_scope, "auth-login")
        self.assertIn("auth-login", throttle.THROTTLE_RATES)
        self.assertIsNotNone(throttle.THROTTLE_RATES["auth-login"])


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
