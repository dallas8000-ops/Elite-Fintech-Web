from django.urls import path

from sacco.views import (
    SaccoMemberDetailView,
    SaccoMemberImportView,
    SaccoMemberLedgerView,
    SaccoMemberListCreateView,
)

urlpatterns = [
    path("", SaccoMemberListCreateView.as_view()),
    path("import/", SaccoMemberImportView.as_view()),
    path("<uuid:member_id>/", SaccoMemberDetailView.as_view()),
    path("<uuid:member_id>/ledger/", SaccoMemberLedgerView.as_view()),
]
