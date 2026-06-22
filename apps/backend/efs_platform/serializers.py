from rest_framework import serializers

from efs_platform.models import OrganizationDomain, SetupTransfer


class DomainSerializer(serializers.ModelSerializer):
    dns_records = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationDomain
        fields = (
            "id", "hostname", "domain_type", "status", "verification_token",
            "is_primary", "verified_at", "created_at", "dns_records",
        )
        read_only_fields = ("id", "status", "verification_token", "verified_at", "created_at")

    def get_dns_records(self, obj: OrganizationDomain) -> list:
        from efs_platform.services.provisioning import dns_records_for_domain

        parts = obj.hostname.split(".", 1)
        base = parts[1] if len(parts) > 1 else obj.hostname
        return dns_records_for_domain(obj, base)


class CreateDomainSerializer(serializers.Serializer):
    base_domain = serializers.CharField(max_length=255)
    api_subdomain = serializers.CharField(max_length=64, default="api")
    app_subdomain = serializers.CharField(max_length=64, default="app")


class VerifyDomainSerializer(serializers.Serializer):
    hostname = serializers.CharField(max_length=255)
    verification_token = serializers.CharField(max_length=64)


class SetupApplySerializer(serializers.Serializer):
    transfer_token = serializers.CharField(required=False)
    target_domain = serializers.CharField(max_length=255, required=False, allow_blank=True)
    upgrade_tier = serializers.ChoiceField(
        choices=["PLATINUM"],
        required=False,
        help_text="Tier upgrade via automation (no domain required)",
    )
    api_subdomain = serializers.CharField(max_length=64, default="api", required=False)
    app_subdomain = serializers.CharField(max_length=64, default="app", required=False)
    automation_agent = serializers.CharField(max_length=128, required=False, allow_blank=True)
    completed_steps = serializers.ListField(child=serializers.CharField(), required=False)

    def validate(self, attrs):
        upgrade = attrs.get("upgrade_tier")
        domain = (attrs.get("target_domain") or "").strip()
        if not upgrade and not domain:
            raise serializers.ValidationError(
                {"target_domain": "Required unless upgrade_tier is set"}
            )
        return attrs


class SetupTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = SetupTransfer
        fields = (
            "transfer_token", "target_domain", "api_subdomain",
            "app_subdomain", "automation_agent", "completed_steps", "updated_at",
        )
