from django.urls import path

from organizations.views import (
    MemberDeleteView,
    MemberInviteView,
    MemberListView,
    MemberRoleView,
    OrganizationDetailView,
)

urlpatterns = [
    path("", OrganizationDetailView.as_view(), name="org-detail"),
    path("members/", MemberListView.as_view(), name="member-list"),
    path("members/invite/", MemberInviteView.as_view(), name="member-invite"),
    path("members/<uuid:member_id>/role/", MemberRoleView.as_view(), name="member-role"),
    path("members/<uuid:member_id>/", MemberDeleteView.as_view(), name="member-delete"),
]
