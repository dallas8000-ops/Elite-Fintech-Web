from rest_framework.permissions import BasePermission

ROLE_HIERARCHY = {
    "VIEWER": 1,
    "MEMBER": 2,
    "ADMIN": 3,
    "OWNER": 4,
}

PERMISSIONS = {
    "billing:read": "VIEWER",
    "billing:manage": "ADMIN",
    "org:manage": "ADMIN",
    "org:delete": "OWNER",
    "members:invite": "ADMIN",
    "members:remove": "ADMIN",
}


def has_minimum_role(user_role: str, required: str) -> bool:
    return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(required, 99)


class HasTenantContext(BasePermission):
    def has_permission(self, request, view):
        if not request.auth:
            return False
        return bool(request.auth.payload.get("organization_id"))


class RequirePermission(BasePermission):
    required_permission = "billing:read"

    def has_permission(self, request, view):
        if not request.auth:
            return False
        role = request.auth.payload.get("role")
        if not role:
            return False
        required_role = PERMISSIONS.get(self.required_permission, "OWNER")
        return has_minimum_role(role, required_role)


class CanReadBilling(RequirePermission):
    required_permission = "billing:read"


class CanManageBilling(RequirePermission):
    required_permission = "billing:manage"


class CanInviteMembers(RequirePermission):
    required_permission = "members:invite"


class CanRemoveMembers(RequirePermission):
    required_permission = "members:remove"
