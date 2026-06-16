from django.urls import path

from efs_platform.views import (
    CapabilitiesView,
    DomainListView,
    DomainVerifyView,
    OpenApiView,
    SetupApplyView,
    SetupTransferView,
)

urlpatterns = [
    path("capabilities/", CapabilitiesView.as_view()),
    path("openapi/", OpenApiView.as_view()),
    path("setup/", SetupTransferView.as_view()),
    path("setup/apply/", SetupApplyView.as_view()),
    path("domains/", DomainListView.as_view()),
    path("domains/verify/", DomainVerifyView.as_view()),
]
