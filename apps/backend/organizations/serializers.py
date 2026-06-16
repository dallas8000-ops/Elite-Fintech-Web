from rest_framework import serializers

from accounts.models import User
from accounts.serializers import UserSerializer
from organizations.models import Membership, Role


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
