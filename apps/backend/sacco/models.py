import uuid

from django.conf import settings
from django.db import models


class MomoNetwork(models.TextChoices):
    MTN = "MTN", "MTN"
    AIRTEL = "AIRTEL", "Airtel"
    UNKNOWN = "UNKNOWN", "Unknown"


class MemberStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    SUSPENDED = "SUSPENDED", "Suspended"


class ProductFrequency(models.TextChoices):
    ONE_TIME = "ONE_TIME", "One time"
    MONTHLY = "MONTHLY", "Monthly"


class PaymentIntentStatus(models.TextChoices):
    INITIATED = "INITIATED", "Initiated"
    PENDING = "PENDING", "Pending"
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"
    EXPIRED = "EXPIRED", "Expired"
    CANCELLED = "CANCELLED", "Cancelled"


class CollectionProvider(models.TextChoices):
    FLUTTERWAVE = "FLUTTERWAVE", "Flutterwave"
    PESAPAL = "PESAPAL", "Pesapal"


class LedgerEntryType(models.TextChoices):
    CREDIT = "CREDIT", "Credit"
    DEBIT = "DEBIT", "Debit"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"
    REFUND = "REFUND", "Refund"


class SaccoMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="sacco_members"
    )
    member_number = models.CharField(max_length=32)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    momo_network = models.CharField(max_length=16, choices=MomoNetwork.choices, default=MomoNetwork.UNKNOWN)
    status = models.CharField(max_length=16, choices=MemberStatus.choices, default=MemberStatus.ACTIVE)
    joined_at = models.DateField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sacco_members"
        constraints = [
            models.UniqueConstraint(fields=["organization", "member_number"], name="uniq_org_member_number"),
            models.UniqueConstraint(fields=["organization", "phone"], name="uniq_org_member_phone"),
        ]
        ordering = ["member_number"]

    def __str__(self) -> str:
        return f"{self.member_number} — {self.full_name}"


class CollectionProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="collection_products"
    )
    name = models.CharField(max_length=255)
    amount_minor = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="ugx")
    frequency = models.CharField(max_length=16, choices=ProductFrequency.choices, default=ProductFrequency.MONTHLY)
    vat_inclusive = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "collection_products"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class PaymentIntent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    idempotency_key = models.CharField(max_length=64)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="payment_intents"
    )
    member = models.ForeignKey(SaccoMember, on_delete=models.PROTECT, related_name="payment_intents")
    product = models.ForeignKey(
        CollectionProduct, on_delete=models.SET_NULL, null=True, blank=True, related_name="payment_intents"
    )
    amount_minor = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="ugx")
    rail = models.CharField(max_length=32, default="MOBILE_MONEY")
    provider = models.CharField(max_length=16, choices=CollectionProvider.choices, default=CollectionProvider.FLUTTERWAVE)
    status = models.CharField(
        max_length=16, choices=PaymentIntentStatus.choices, default=PaymentIntentStatus.INITIATED
    )
    provider_reference = models.CharField(max_length=128, unique=True)
    provider_transaction_id = models.CharField(max_length=128, blank=True, null=True, unique=True)
    phone = models.CharField(max_length=20)
    purpose = models.CharField(max_length=128, blank=True)
    expires_at = models.DateTimeField()
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_payment_intents"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payment_intents"
        constraints = [
            models.UniqueConstraint(fields=["organization", "idempotency_key"], name="uniq_org_idempotency_key"),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.provider_reference} ({self.status})"


class LedgerEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="ledger_entries"
    )
    member = models.ForeignKey(SaccoMember, on_delete=models.PROTECT, related_name="ledger_entries")
    payment_intent = models.ForeignKey(
        PaymentIntent, on_delete=models.SET_NULL, null=True, blank=True, related_name="ledger_entries"
    )
    entry_type = models.CharField(max_length=16, choices=LedgerEntryType.choices)
    amount_minor = models.PositiveIntegerField()
    balance_after = models.IntegerField()
    description = models.CharField(max_length=255)
    external_reference = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ledger_entries"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.entry_type} {self.amount_minor} → {self.balance_after}"
