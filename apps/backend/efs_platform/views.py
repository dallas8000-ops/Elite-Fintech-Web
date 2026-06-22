from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import CanManageBilling, HasTenantContext
from efs_platform.models import DomainStatus, DomainType, OrganizationDomain, SetupTransfer
from efs_platform.serializers import (
    CreateDomainSerializer,
    DomainSerializer,
    SetupApplySerializer,
    VerifyDomainSerializer,
)
from config.readiness import readiness_summary
from efs_platform.services.provisioning import build_setup_manifest
from efs_platform.services.tier_upgrade import apply_platinum_upgrade, build_platinum_upgrade_manifest
from efs_platform.services.tier import get_platform_profile
from organizations.models import Organization


def org_id(request) -> str:
    return request.auth.payload["organization_id"]


class CapabilitiesView(APIView):
    """Public — tier positioning for initial review."""

    permission_classes = [AllowAny]

    def get(self, request):
        profile = get_platform_profile()
        profile["setup_api"] = request.build_absolute_uri("/api/v1/platform/setup/")
        profile["readiness_api"] = request.build_absolute_uri("/api/v1/platform/readiness/")
        readiness = readiness_summary()
        profile["deployment_readiness"] = {
            "score": readiness["score"],
            "tier": readiness["deployment_tier"],
            "gaps": readiness["gaps"][:5],
        }
        return Response(profile)


class ReadinessView(APIView):
    """Public — production readiness score and upgrade gaps."""

    permission_classes = [AllowAny]

    def get(self, request):
        summary = readiness_summary()
        profile = get_platform_profile()
        summary["platform_tier"] = profile["tier"]
        summary["next_tier"] = profile.get("next_tier")
        summary["upgrade_hints"] = profile.get("upgrade_hints", [])
        summary["health_api"] = request.build_absolute_uri("/health/")
        return Response(summary)


class OpenApiView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        base = request.build_absolute_uri("/api/v1").rstrip("/")
        return Response({
            "openapi": "3.1.0",
            "info": {
                "title": "Elite Fintech Systems API",
                "version": "1.0.0",
                "description": "ENTERPRISE tier — African fintech billing with domain linking & automation setup.",
            },
            "paths": {
                "/platform/capabilities/": {"get": {"summary": "Platform tier & capabilities"}},
                "/platform/readiness/": {"get": {"summary": "Production readiness score & upgrade gaps"}},
                "/platform/setup/": {"get": {"summary": "Setup transfer manifest (auth)"}},
                "/platform/setup/apply/": {"post": {"summary": "Apply domain + automation setup"}},
                "/platform/domains/": {"get": {"summary": "List org domains"}, "post": {"summary": "Create domains"}},
                "/platform/domains/verify/": {"post": {"summary": "Verify domain ownership"}},
                "/auth/register/": {"post": {"summary": "Register SA org"}},
                "/billing/checkout/": {"post": {"summary": "Rail-first checkout"}},
            },
            "servers": [{"url": base}],
        })


class SetupTransferView(APIView):
    permission_classes = [HasTenantContext, CanManageBilling]

    def get(self, request):
        org = Organization.objects.get(id=org_id(request))
        transfer, _ = SetupTransfer.objects.get_or_create(organization=org)
        manifest = build_setup_manifest(org, transfer, request)
        return Response(manifest)

    def post(self, request):
        """Initiate or refresh setup transfer for AI agents."""
        org = Organization.objects.get(id=org_id(request))
        transfer, _ = SetupTransfer.objects.get_or_create(organization=org)
        serializer = SetupApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data.get("target_domain"):
            transfer.target_domain = data["target_domain"]
        if data.get("api_subdomain"):
            transfer.api_subdomain = data["api_subdomain"]
        if data.get("app_subdomain"):
            transfer.app_subdomain = data["app_subdomain"]
        if data.get("automation_agent"):
            transfer.automation_agent = data["automation_agent"]
        transfer.save()

        return Response(build_setup_manifest(org, transfer, request), status=status.HTTP_200_OK)


class SetupApplyView(APIView):
    """AI automation endpoint — link domain, create DNS records, return env manifest."""

    permission_classes = [HasTenantContext, CanManageBilling]

    def post(self, request):
        org = Organization.objects.get(id=org_id(request))
        serializer = SetupApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        transfer, _ = SetupTransfer.objects.get_or_create(organization=org)
        if data.get("transfer_token") and data["transfer_token"] != transfer.transfer_token:
            return Response({"error": "Invalid transfer token"}, status=status.HTTP_403_FORBIDDEN)

        if data.get("automation_agent"):
            transfer.automation_agent = data["automation_agent"]
        if data.get("completed_steps"):
            transfer.completed_steps = list(set(transfer.completed_steps + data["completed_steps"]))

        upgrade_tier = data.get("upgrade_tier")
        if upgrade_tier == "PLATINUM":
            apply_platinum_upgrade(transfer, data.get("completed_steps"))
            transfer.save()
            manifest = build_platinum_upgrade_manifest(org, transfer, request)
            manifest["message"] = (
                f"PLATINUM upgrade applied via automation ({transfer.automation_agent or 'agent'}). "
                "Deploy environment variables from deploy_actions, then redeploy."
            )
            return Response(manifest, status=status.HTTP_200_OK)

        base = data.get("target_domain", "").strip()
        if not base:
            return Response({"error": "target_domain required for domain setup"}, status=status.HTTP_400_BAD_REQUEST)

        transfer.target_domain = base
        transfer.api_subdomain = data.get("api_subdomain", "api")
        transfer.app_subdomain = data.get("app_subdomain", "app")
        if data.get("automation_agent"):
            transfer.automation_agent = data["automation_agent"]
        if data.get("completed_steps"):
            transfer.completed_steps = list(set(transfer.completed_steps + data["completed_steps"]))
        transfer.save()

        api_host = f"{transfer.api_subdomain}.{base}"
        app_host = f"{transfer.app_subdomain}.{base}"

        for hostname, dtype in [(api_host, DomainType.API), (app_host, DomainType.APP)]:
            OrganizationDomain.objects.get_or_create(
                organization=org,
                hostname=hostname,
                defaults={"domain_type": dtype, "is_primary": True},
            )

        if "domain_claim" not in transfer.completed_steps:
            transfer.completed_steps.append("domain_claim")
            transfer.save(update_fields=["completed_steps", "updated_at"])

        manifest = build_setup_manifest(org, transfer, request)
        manifest["message"] = (
            f"Domain linked. Add DNS records at your registrar for {base}, "
            "then POST /platform/domains/verify/ to confirm."
        )
        return Response(manifest, status=status.HTTP_200_OK)


class DomainListView(APIView):
    permission_classes = [HasTenantContext, CanManageBilling]

    def get(self, request):
        domains = OrganizationDomain.objects.filter(organization_id=org_id(request))
        return Response({"domains": DomainSerializer(domains, many=True).data})

    def post(self, request):
        org = Organization.objects.get(id=org_id(request))
        serializer = CreateDomainSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        base = data["base_domain"].lower().strip()

        created = []
        for sub, dtype in [(data["api_subdomain"], DomainType.API), (data["app_subdomain"], DomainType.APP)]:
            hostname = f"{sub}.{base}"
            domain, _ = OrganizationDomain.objects.get_or_create(
                organization=org,
                hostname=hostname,
                defaults={"domain_type": dtype, "is_primary": True},
            )
            created.append(domain)

        return Response(
            {"domains": DomainSerializer(created, many=True).data},
            status=status.HTTP_201_CREATED,
        )


class DomainVerifyView(APIView):
    permission_classes = [HasTenantContext, CanManageBilling]

    def post(self, request):
        serializer = VerifyDomainSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        domain = OrganizationDomain.objects.filter(
            organization_id=org_id(request),
            hostname=data["hostname"],
        ).first()
        if not domain:
            return Response({"error": "Domain not found"}, status=status.HTTP_404_NOT_FOUND)

        if domain.verification_token != data["verification_token"]:
            domain.status = DomainStatus.FAILED
            domain.save(update_fields=["status"])
            return Response({"error": "Invalid verification token"}, status=status.HTTP_400_BAD_REQUEST)

        domain.status = DomainStatus.VERIFIED
        domain.verified_at = timezone.now()
        domain.save()

        transfer = SetupTransfer.objects.filter(organization_id=org_id(request)).first()
        if transfer and "dns_verify" not in transfer.completed_steps:
            transfer.completed_steps.append("dns_verify")
            transfer.save(update_fields=["completed_steps", "updated_at"])

        return Response({
            "verified": True,
            "hostname": domain.hostname,
            "production_urls": {
                "api": f"https://{domain.hostname}" if domain.domain_type == DomainType.API else None,
            },
        })
