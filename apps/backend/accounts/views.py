from datetime import datetime, timezone

from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from accounts.serializers import LoginSerializer, RegisterSerializer, UserSerializer
from organizations.models import Membership, Organization, Role


def build_tokens(user: User, organization_id: str, role: str) -> dict:
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


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if User.objects.filter(email=data["email"]).exists():
            return Response({"error": "Email already registered"}, status=status.HTTP_409_CONFLICT)

        slug_base = data["organization_name"].lower().replace(" ", "-")[:48]
        slug = f"{slug_base}-{int(datetime.now(timezone.utc).timestamp())}"

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

        tokens = build_tokens(user, str(org.id), Role.OWNER)

        return Response(
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


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

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
            memberships.filter(organization_id=org_id).first()
            if org_id
            else memberships.first()
        )
        if not membership:
            return Response({"error": "Not a member of this organization"}, status=status.HTTP_403_FORBIDDEN)

        tokens = build_tokens(user, str(membership.organization_id), membership.role)

        return Response(
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
                    {
                        "id": str(m.organization_id),
                        "name": m.organization.name,
                        "role": m.role,
                    }
                    for m in memberships
                ],
            }
        )


class MeView(APIView):
    def get(self, request):
        org_id = request.auth.payload.get("organization_id")
        role = request.auth.payload.get("role")

        membership = Membership.objects.filter(
            user=request.user, organization_id=org_id
        ).select_related("organization").first()

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
