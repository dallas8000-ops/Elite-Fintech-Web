from rest_framework import serializers

from accounts.models import User
from accounts.serializers import UserSerializer
from organizations.models import Membership, Organization, Role


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = (
            "id",
            "name",
            "slug",
            "country",
            "province",
            "industry_sector",
            "cipc_registration_number",
            "vat_number",
            "fica_status",
            "popia_consent_at",
        )
        read_only_fields = ("id", "slug", "fica_status", "popia_consent_at")


class OrganizationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = (
            "name",
            "province",
            "industry_sector",
            "cipc_registration_number",
            "vat_number",
        )


class MemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ("id", "role", "user", "created_at")


class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField(max_length=255)
    password = serializers.CharField(min_length=8, write_only=True)
    role = serializers.ChoiceField(choices=[Role.ADMIN, Role.MEMBER, Role.VIEWER])


class UpdateRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[Role.ADMIN, Role.MEMBER, Role.VIEWER])
