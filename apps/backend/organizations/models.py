import uuid

from django.db import models


class Role(models.TextChoices):
    OWNER = "OWNER", "Owner"
    ADMIN = "ADMIN", "Admin"
    MEMBER = "MEMBER", "Member"
    VIEWER = "VIEWER", "Viewer"


class SaProvince(models.TextChoices):
    GAUTENG = "GAUTENG", "Gauteng"
    WESTERN_CAPE = "WESTERN_CAPE", "Western Cape"
    KWAZULU_NATAL = "KWAZULU_NATAL", "KwaZulu-Natal"
    EASTERN_CAPE = "EASTERN_CAPE", "Eastern Cape"
    LIMPOPO = "LIMPOPO", "Limpopo"
    MPUMALANGA = "MPUMALANGA", "Mpumalanga"
    NORTH_WEST = "NORTH_WEST", "North West"
    FREE_STATE = "FREE_STATE", "Free State"
    NORTHERN_CAPE = "NORTHERN_CAPE", "Northern Cape"


class FicaStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=64)
    cipc_registration_number = models.CharField(max_length=32, blank=True, null=True)
    vat_number = models.CharField(max_length=16, blank=True, null=True)
    province = models.CharField(max_length=32, default="CENTRAL")
    country = models.CharField(max_length=2, default="UG")
    industry_sector = models.CharField(max_length=255, blank=True)
    popia_consent_at = models.DateTimeField(blank=True, null=True)
    fica_status = models.CharField(max_length=16, choices=FicaStatus.choices, default=FicaStatus.PENDING)
    fica_verified_at = models.DateTimeField(blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=64, blank=True, null=True, unique=True)
    payfast_token = models.CharField(max_length=128, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations"

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="memberships")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="members")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "memberships"
        unique_together = ("user", "organization")

    def __str__(self) -> str:
        return f"{self.user.email} @ {self.organization.name} ({self.role})"
