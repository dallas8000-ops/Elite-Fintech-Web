import secrets
import uuid

from django.db import models


class DomainType(models.TextChoices):
    APP = "APP", "Dashboard (app)"
    API = "API", "API (api)"


class DomainStatus(models.TextChoices):
    PENDING = "PENDING", "Pending DNS"
    VERIFYING = "VERIFYING", "Verifying"
    VERIFIED = "VERIFIED", "Verified"
    FAILED = "FAILED", "Failed"


class OrganizationDomain(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="domains"
    )
    hostname = models.CharField(max_length=255)
    domain_type = models.CharField(max_length=8, choices=DomainType.choices)
    status = models.CharField(max_length=16, choices=DomainStatus.choices, default=DomainStatus.PENDING)
    verification_token = models.CharField(max_length=64, blank=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "organization_domains"
        unique_together = ("organization", "hostname")

    def save(self, *args, **kwargs):
        if not self.verification_token:
            self.verification_token = secrets.token_hex(16)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.hostname} ({self.domain_type})"


class SetupTransfer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        "organizations.Organization", on_delete=models.CASCADE, related_name="setup_transfer"
    )
    transfer_token = models.CharField(max_length=64, unique=True, blank=True)
    target_domain = models.CharField(max_length=255, blank=True)
    api_subdomain = models.CharField(max_length=64, default="api")
    app_subdomain = models.CharField(max_length=64, default="app")
    automation_agent = models.CharField(max_length=128, blank=True)
    completed_steps = models.JSONField(default=list)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.transfer_token:
            self.transfer_token = f"efs_{secrets.token_urlsafe(24)}"
        super().save(*args, **kwargs)

    class Meta:
        db_table = "setup_transfers"
