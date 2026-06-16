from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import CanInviteMembers, CanReadBilling, CanRemoveMembers, HasTenantContext
from organizations.models import Membership, Role
from organizations.serializers import InviteMemberSerializer, MemberSerializer, UpdateRoleSerializer


def get_org_id(request) -> str:
    return request.auth.payload["organization_id"]


class MemberListView(APIView):
    permission_classes = [HasTenantContext, CanReadBilling]

    def get(self, request):
        members = Membership.objects.filter(
            organization_id=get_org_id(request)
        ).select_related("user").order_by("created_at")
        return Response({"members": MemberSerializer(members, many=True).data})


class MemberInviteView(APIView):
    permission_classes = [HasTenantContext, CanInviteMembers]

    @transaction.atomic
    def post(self, request):
        serializer = InviteMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        org_id = get_org_id(request)

        if Membership.objects.filter(
            organization_id=org_id, user__email=data["email"]
        ).exists():
            return Response({"error": "User is already a member"}, status=status.HTTP_409_CONFLICT)

        user, _ = User.objects.get_or_create(
            email=data["email"],
            defaults={"name": data["name"]},
        )
        if not user.has_usable_password():
            user.set_password(data["password"])
            user.name = data["name"]
            user.save()

        membership = Membership.objects.create(
            user=user,
            organization_id=org_id,
            role=data["role"],
        )
        return Response(
            {"member": MemberSerializer(membership).data},
            status=status.HTTP_201_CREATED,
        )


class MemberRoleView(APIView):
    permission_classes = [HasTenantContext, CanInviteMembers]

    def patch(self, request, member_id):
        serializer = UpdateRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership = Membership.objects.filter(
            id=member_id, organization_id=get_org_id(request)
        ).first()
        if not membership:
            return Response({"error": "Member not found"}, status=status.HTTP_404_NOT_FOUND)
        if membership.role == Role.OWNER:
            return Response({"error": "Cannot change owner role"}, status=status.HTTP_403_FORBIDDEN)

        membership.role = serializer.validated_data["role"]
        membership.save()
        return Response({"member": MemberSerializer(membership).data})


class MemberDeleteView(APIView):
    permission_classes = [HasTenantContext, CanRemoveMembers]

    def delete(self, request, member_id):
        membership = Membership.objects.filter(
            id=member_id, organization_id=get_org_id(request)
        ).first()
        if not membership:
            return Response({"error": "Member not found"}, status=status.HTTP_404_NOT_FOUND)
        if membership.role == Role.OWNER:
            return Response({"error": "Cannot remove organization owner"}, status=status.HTTP_403_FORBIDDEN)

        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
