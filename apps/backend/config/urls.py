from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/billing/", include("billing.urls")),
    path("api/v1/members/", include("sacco.member_urls")),
    path("api/v1/collections/", include("sacco.urls")),
    path("api/v1/org/", include("organizations.urls")),
    path("api/v1/platform/", include("efs_platform.urls")),
    path("webhooks/", include("billing.webhook_urls")),
    path("health/", include("config.health_urls")),
]
