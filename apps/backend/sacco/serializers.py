import csv
import io

from rest_framework import serializers

from sacco.models import CollectionProduct, LedgerEntry, PaymentIntent, SaccoMember
from sacco.services.ledger import member_balance


class SaccoMemberSerializer(serializers.ModelSerializer):
    balance_minor = serializers.SerializerMethodField()
    momoNetwork = serializers.CharField(source="momo_network")
    memberNumber = serializers.CharField(source="member_number")
    fullName = serializers.CharField(source="full_name")
    joinedAt = serializers.DateField(source="joined_at")

    class Meta:
        model = SaccoMember
        fields = (
            "id",
            "memberNumber",
            "fullName",
            "phone",
            "momoNetwork",
            "status",
            "joinedAt",
            "balance_minor",
            "metadata",
        )
        read_only_fields = ("id", "joinedAt", "balance_minor")

    def get_balance_minor(self, obj: SaccoMember) -> int:
        return member_balance(obj)


class SaccoMemberCreateSerializer(serializers.ModelSerializer):
    member_number = serializers.CharField(max_length=32)
    full_name = serializers.CharField(max_length=255)
    momo_network = serializers.ChoiceField(choices=["MTN", "AIRTEL", "UNKNOWN"], default="UNKNOWN")

    class Meta:
        model = SaccoMember
        fields = ("member_number", "full_name", "phone", "momo_network", "status", "metadata")


class CollectionProductSerializer(serializers.ModelSerializer):
    amountMinor = serializers.IntegerField(source="amount_minor")
    vatInclusive = serializers.BooleanField(source="vat_inclusive")
    isActive = serializers.BooleanField(source="is_active")

    class Meta:
        model = CollectionProduct
        fields = ("id", "name", "amountMinor", "currency", "frequency", "vatInclusive", "isActive")
        read_only_fields = ("id",)


class LedgerEntrySerializer(serializers.ModelSerializer):
    entryType = serializers.CharField(source="entry_type")
    amountMinor = serializers.IntegerField(source="amount_minor")
    balanceAfter = serializers.IntegerField(source="balance_after")
    externalReference = serializers.CharField(source="external_reference")
    createdAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = LedgerEntry
        fields = ("id", "entryType", "amountMinor", "balanceAfter", "description", "externalReference", "createdAt")


class PaymentIntentSerializer(serializers.ModelSerializer):
    intentId = serializers.UUIDField(source="id")
    amountMinor = serializers.IntegerField(source="amount_minor")
    providerReference = serializers.CharField(source="provider_reference")
    providerTransactionId = serializers.CharField(source="provider_transaction_id", allow_null=True)
    expiresAt = serializers.DateTimeField(source="expires_at")
    createdAt = serializers.DateTimeField(source="created_at")
    member = SaccoMemberSerializer(read_only=True)
    memberId = serializers.UUIDField(source="member_id", read_only=True)

    class Meta:
        model = PaymentIntent
        fields = (
            "intentId",
            "status",
            "amountMinor",
            "currency",
            "rail",
            "provider",
            "providerReference",
            "providerTransactionId",
            "phone",
            "purpose",
            "expiresAt",
            "createdAt",
            "member",
            "memberId",
            "metadata",
        )


class InitiateCollectionSerializer(serializers.Serializer):
    member_id = serializers.UUIDField()
    product_id = serializers.UUIDField(required=False, allow_null=True)
    amount_minor = serializers.IntegerField(min_value=1000, required=False)
    purpose = serializers.CharField(max_length=128, required=False, allow_blank=True)
    idempotency_key = serializers.CharField(max_length=64, required=False, allow_blank=True)

    def validate(self, attrs):
        product_id = attrs.get("product_id")
        amount = attrs.get("amount_minor")
        if not product_id and not amount:
            raise serializers.ValidationError("Provide product_id or amount_minor.")
        return attrs


class MemberImportSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, uploaded):
        if not uploaded.name.lower().endswith(".csv"):
            raise serializers.ValidationError("Upload a CSV file.")
        if uploaded.size > 512_000:
            raise serializers.ValidationError("CSV must be under 512KB.")
        return uploaded


def parse_members_csv(file_obj) -> list[dict]:
    text = io.StringIO(file_obj.read().decode("utf-8-sig"))
    reader = csv.DictReader(text)
    required = {"member_number", "full_name", "phone"}
    if not reader.fieldnames or not required.issubset({h.strip().lower() for h in reader.fieldnames}):
        raise serializers.ValidationError(
            "CSV must include columns: member_number, full_name, phone (optional: momo_network)"
        )
    rows = []
    for row in reader:
        normalized = {k.strip().lower(): (v or "").strip() for k, v in row.items()}
        rows.append(
            {
                "member_number": normalized.get("member_number", ""),
                "full_name": normalized.get("full_name", ""),
                "phone": normalized.get("phone", ""),
                "momo_network": (normalized.get("momo_network") or "UNKNOWN").upper(),
            }
        )
    return rows
