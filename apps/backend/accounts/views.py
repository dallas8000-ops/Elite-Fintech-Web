from datetime import datetime, timezone
import logging
import time

from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.db.utils import OperationalError
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.cookies import REFRESH_COOKIE_NAME, clear_refresh_cookie, set_refresh_cookie
from accounts.models import RevokedRefreshToken, User
from accounts.serializers import LoginSerializer, RegisterSerializer, UserSerializer
from organizations.models import Membership, Organization, Role

logger = logging.getLogger(__name__)


def build_tokens(user: User, organization_id: str, role: str) -> dict:
    """Mint a fresh access+refresh pair bound to the given org/role context.

    The refresh token is set as an httpOnly cookie by the caller — never
    returned in the JSON body.
    """
    refresh = RefreshToken.for_user(user)
    refresh["organization_id"] = str(organization_id)
    refresh["role"] = role
    refresh["email"] = user.email
    access = refresh.access_token
    access["organization_id"] = str(organization_id)
    access["role"] = role
    access["email"] = user.email
    return {
        "access": str(access),
        "refresh": str(refresh),
        "token": str(access),
    }


def _attach_tokens(response: Response, tokens: dict) -> Response:
    """Strip the refresh token from the JSON body and set it as a cookie."""
    refresh_token = tokens.pop("refresh", None)
    if isinstance(response.data, dict):
        response.data = {k: v for k, v in response.data.items() if k != "refresh"}
    if refresh_token:
        set_refresh_cookie(response, refresh_token)
    return response


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth-register"

    MAX_TRANSIENT_RETRIES = 3
    RETRY_BACKOFF_SECONDS = 0.05

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if User.objects.filter(email=data["email"]).exists():
            return Response({"error": "Email already registered"}, status=status.HTTP_409_CONFLICT)

        slug_base = data["organization_name"].lower().replace(" ", "-")[:48]
        slug = f"{slug_base}-{int(datetime.now(timezone.utc).timestamp())}"

        last_exc: Exception | None = None
        user = org = None
        for attempt in range(self.MAX_TRANSIENT_RETRIES):
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        email=data["email"],
                        password=data["password"],
                        name=data["name"],
                    )
                    org = Organization.objects.create(
                        name=data["organization_name"],
                        slug=slug,
                        country=data.get("country", "UG"),
                        province=data["province"],
                        industry_sector=data.get("industry_sector") or "",
                        cipc_registration_number=data.get("cipc_registration_number") or None,
                        vat_number=data.get("vat_number") or None,
                        popia_consent_at=datetime.now(timezone.utc),
                    )
                    Membership.objects.create(user=user, organization=org, role=Role.OWNER)
                break
            except IntegrityError:
                return Response({"error": "Email already registered"}, status=status.HTTP_409_CONFLICT)
            except OperationalError as exc:
                last_exc = exc
                if attempt < self.MAX_TRANSIENT_RETRIES - 1:
                    time.sleep(self.RETRY_BACKOFF_SECONDS * (2**attempt))
                    continue
                logger.warning(
                    "Register: exhausted retries on transient DB contention for %s: %s",
                    data["email"],
                    exc,
                )
                return Response(
                    {"error": "Registration temporarily unavailable, please retry."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
        else:
            logger.error("Register: retry loop exhausted unexpectedly: %s", last_exc)
            return Response({"error": "Registration failed, please retry."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        tokens = build_tokens(user, str(org.id), Role.OWNER)
        response = Response(
            {
                **tokens,
                "user": UserSerializer(user).data,
                "organization": {
                    "id": str(org.id),
                    "name": org.name,
                    "slug": org.slug,
                    "country": org.country,
                    "province": org.province,
                },
                "role": Role.OWNER,
            },
            status=status.HTTP_201_CREATED,
        )
        return _attach_tokens(response, tokens)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth-login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = authenticate(request, email=data["email"], password=data["password"])
        if not user:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        memberships = Membership.objects.filter(user=user).select_related("organization")
        if not memberships.exists():
            return Response({"error": "No organization membership"}, status=status.HTTP_403_FORBIDDEN)

        org_id = data.get("organization_id")
        membership = (
            memberships.filter(organization_id=org_id).first() if org_id else memberships.first()
        )
        if not membership:
            return Response({"error": "Not a member of this organization"}, status=status.HTTP_403_FORBIDDEN)

        tokens = build_tokens(user, str(membership.organization_id), membership.role)
        response = Response(
            {
                **tokens,
                "user": UserSerializer(user).data,
                "organization": {
                    "id": str(membership.organization.id),
                    "name": membership.organization.name,
                    "slug": membership.organization.slug,
                    "country": membership.organization.country,
                    "province": membership.organization.province,
                },
                "role": membership.role,
                "organizations": [
                    {"id": str(m.organization_id), "name": m.organization.name, "role": m.role}
                    for m in memberships
                ],
            }
        )
        return _attach_tokens(response, tokens)


class RefreshView(APIView):
    """Mint a new access token from the httpOnly refresh cookie.

    Re-verifies organization membership and current role on every refresh.
    """

    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth-refresh"

    ROTATION_GRACE_SECONDS = 10

    def post(self, request):
        raw_refresh = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not raw_refresh:
            return Response({"error": "No refresh token"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            unverified = RefreshToken(raw_refresh, verify=False)
        except TokenError:
            response = Response({"error": "Invalid or expired refresh token"}, status=status.HTTP_401_UNAUTHORIZED)
            clear_refresh_cookie(response)
            return response

        jti = unverified.payload.get("jti")
        if jti and RevokedRefreshToken.objects.filter(jti=jti).exists():
            response = Response({"error": "Token has been revoked"}, status=status.HTTP_401_UNAUTHORIZED)
            clear_refresh_cookie(response)
            return response

        within_grace = self._was_blacklisted_within_grace_window(unverified)

        if not within_grace:
            try:
                refresh = RefreshToken(raw_refresh)
            except TokenError:
                response = Response(
                    {"error": "Invalid or expired refresh token"}, status=status.HTTP_401_UNAUTHORIZED
                )
                clear_refresh_cookie(response)
                return response
        else:
            refresh = unverified

        user_id = refresh.payload.get("user_id")
        org_id = refresh.payload.get("organization_id")

        membership = (
            Membership.objects.filter(user_id=user_id, organization_id=org_id)
            .select_related("organization")
            .first()
        )
        if not membership:
            response = Response(
                {"error": "Organization membership no longer valid"},
                status=status.HTTP_403_FORBIDDEN,
            )
            clear_refresh_cookie(response)
            return response

        user = User.objects.filter(id=user_id).first()
        if not user or not user.is_active:
            response = Response({"error": "Account inactive"}, status=status.HTTP_403_FORBIDDEN)
            clear_refresh_cookie(response)
            return response

        if within_grace:
            access = self._access_token_for(user, membership)
            return Response({"access": str(access), "token": str(access), "role": membership.role})

        tokens = build_tokens(user, str(membership.organization_id), membership.role)
        try:
            refresh.blacklist()
        except AttributeError:
            pass

        response = Response({"access": tokens["access"], "token": tokens["access"], "role": membership.role})
        return _attach_tokens(response, tokens)

    @staticmethod
    def _was_blacklisted_within_grace_window(token: RefreshToken) -> bool:
        try:
            from django.utils import timezone as django_tz

            from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
        except ImportError:
            return False

        jti = token.payload.get("jti")
        if not jti:
            return False
        blacklisted = BlacklistedToken.objects.filter(token__jti=jti).select_related("token").first()
        if not blacklisted:
            return False
        age = django_tz.now() - blacklisted.blacklisted_at
        return age.total_seconds() <= RefreshView.ROTATION_GRACE_SECONDS

    @staticmethod
    def _access_token_for(user: User, membership):
        from rest_framework_simplejwt.tokens import AccessToken

        access = AccessToken.for_user(user)
        access["organization_id"] = str(membership.organization_id)
        access["role"] = membership.role
        access["email"] = user.email
        return access


class LogoutView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        raw_refresh = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if raw_refresh:
            try:
                token = RefreshToken(raw_refresh, verify=False)
                jti = token.payload.get("jti")
                if jti:
                    RevokedRefreshToken.objects.get_or_create(jti=jti)
                token.blacklist()
            except (TokenError, AttributeError):
                pass

        response = Response({"detail": "Logged out"}, status=status.HTTP_200_OK)
        clear_refresh_cookie(response)
        return response


class MeView(APIView):
    def get(self, request):
        org_id = request.auth.payload.get("organization_id")
        role = request.auth.payload.get("role")

        membership = (
            Membership.objects.filter(user=request.user, organization_id=org_id)
            .select_related("organization")
            .first()
        )

        if not membership:
            return Response({"error": "Organization context invalid"}, status=status.HTTP_403_FORBIDDEN)

        org = membership.organization
        return Response(
            {
                "user": UserSerializer(request.user).data,
                "organization": {
                    "id": str(org.id),
                    "name": org.name,
                    "slug": org.slug,
                    "country": org.country,
                    "province": org.province,
                    "industry_sector": org.industry_sector,
                    "cipc_registration_number": org.cipc_registration_number,
                    "vat_number": org.vat_number,
                    "fica_status": org.fica_status,
                    "popia_consent_at": org.popia_consent_at,
                },
                "role": role,
            }
        )
