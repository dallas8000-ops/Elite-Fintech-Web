from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import CanManageBilling, CanReadBilling, HasTenantContext
from sacco.models import CollectionProduct, PaymentIntent, PaymentIntentStatus, SaccoMember
from sacco.serializers import (
    CollectionProductSerializer,
    InitiateCollectionSerializer,
    LedgerEntrySerializer,
    MemberImportSerializer,
    PaymentIntentSerializer,
    SaccoMemberCreateSerializer,
    SaccoMemberSerializer,
    parse_members_csv,
)
from sacco.services.intents import initiate_collection, maybe_verify_pending_intent
from sacco.services.ledger import member_balance
from sacco.services.payments.flutterwave import is_flutterwave_configured
from sacco.services.receipts import build_receipt
from organizations.models import Organization


def org_id(request) -> str:
    return request.auth.payload["organization_id"]


class SaccoMemberListCreateView(APIView):
    permission_classes = [HasTenantContext, CanReadBilling]

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasTenantContext(), CanManageBilling()]
        return super().get_permissions()

    def get(self, request):
        oid = org_id(request)
        qs = SaccoMember.objects.filter(organization_id=oid)
        q = request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(full_name__icontains=q) | Q(member_number__icontains=q) | Q(phone__icontains=q)
            )
        members = qs[:500]
        return Response({"members": SaccoMemberSerializer(members, many=True).data})

    def post(self, request):
        oid = org_id(request)
        serializer = SaccoMemberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = serializer.save(organization_id=oid)
        return Response(SaccoMemberSerializer(member).data, status=status.HTTP_201_CREATED)


class SaccoMemberImportView(APIView):
    permission_classes = [HasTenantContext, CanManageBilling]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        oid = org_id(request)
        serializer = MemberImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            rows = parse_members_csv(serializer.validated_data["file"])
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        created = 0
        errors: list[str] = []
        for idx, row in enumerate(rows, start=2):
            if not row["member_number"] or not row["full_name"] or not row["phone"]:
                errors.append(f"Row {idx}: missing required fields")
                continue
            try:
                SaccoMember.objects.create(
                    organization_id=oid,
                    member_number=row["member_number"],
                    full_name=row["full_name"],
                    phone=row["phone"],
                    momo_network=row["momo_network"] if row["momo_network"] in ("MTN", "AIRTEL") else "UNKNOWN",
                )
                created += 1
            except Exception as exc:
                errors.append(f"Row {idx}: {exc}")

        return Response({"created": created, "errors": errors})


class SaccoMemberDetailView(APIView):
    permission_classes = [HasTenantContext, CanReadBilling]

    def get(self, request, member_id):
        oid = org_id(request)
        member = get_object_or_404(SaccoMember, id=member_id, organization_id=oid)
        data = SaccoMemberSerializer(member).data
        data["balance_minor"] = member_balance(member)
        return Response(data)


class SaccoMemberLedgerView(APIView):
    permission_classes = [HasTenantContext, CanManageBilling]

    def get(self, request, member_id):
        oid = org_id(request)
        member = get_object_or_404(SaccoMember, id=member_id, organization_id=oid)
        entries = member.ledger_entries.all()[:200]
        return Response({"entries": LedgerEntrySerializer(entries, many=True).data})


class CollectionProductListCreateView(APIView):
    permission_classes = [HasTenantContext, CanReadBilling]

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasTenantContext(), CanManageBilling()]
        return super().get_permissions()

    def get(self, request):
        oid = org_id(request)
        products = CollectionProduct.objects.filter(organization_id=oid, is_active=True)
        return Response({"products": CollectionProductSerializer(products, many=True).data})

    def post(self, request):
        oid = org_id(request)
        serializer = CollectionProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = CollectionProduct.objects.create(organization_id=oid, **serializer.validated_data)
        return Response(CollectionProductSerializer(product).data, status=status.HTTP_201_CREATED)


class InitiateCollectionView(APIView):
    permission_classes = [HasTenantContext, CanManageBilling]

    def post(self, request):
        if not is_flutterwave_configured():
            return Response(
                {
                    "error": "Flutterwave not configured. Add FLUTTERWAVE_SECRET_KEY to .env.",
                    "provider": "FLUTTERWAVE",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        oid = org_id(request)
        org = get_object_or_404(Organization, id=oid)
        serializer = InitiateCollectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        member = get_object_or_404(SaccoMember, id=data["member_id"], organization_id=oid)
        product = None
        amount = data.get("amount_minor")
        if data.get("product_id"):
            product = get_object_or_404(CollectionProduct, id=data["product_id"], organization_id=oid)
            amount = product.amount_minor

        purpose = data.get("purpose") or (product.name if product else "Collection")

        try:
            intent = initiate_collection(
                organization=org,
                member=member,
                product=product,
                amount_minor=amount,
                purpose=purpose,
                created_by=request.user,
                idempotency_key=data.get("idempotency_key") or None,
            )
        except RuntimeError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as exc:
            return Response({"error": f"MoMo initiation failed: {exc}"}, status=status.HTTP_502_BAD_GATEWAY)

        message = getattr(intent, "_charge_message", "Check phone for MoMo prompt")
        payment_url = getattr(intent, "_payment_url", None)

        return Response(
            {
                "intent_id": str(intent.id),
                "status": intent.status,
                "provider": intent.provider,
                "payment_url": payment_url,
                "message": message,
                "expires_at": intent.expires_at.isoformat(),
                "intent": PaymentIntentSerializer(intent).data,
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentIntentListView(APIView):
    permission_classes = [HasTenantContext, CanManageBilling]

    def get(self, request):
        oid = org_id(request)
        qs = PaymentIntent.objects.filter(organization_id=oid).select_related("member")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        if request.query_params.get("today") == "1":
            start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            qs = qs.filter(created_at__gte=start)

        intents = qs[:100]
        return Response({"intents": PaymentIntentSerializer(intents, many=True).data})


class PaymentIntentDetailView(APIView):
    permission_classes = [HasTenantContext, CanManageBilling]

    def get(self, request, intent_id):
        oid = org_id(request)
        intent = get_object_or_404(
            PaymentIntent.objects.select_related("member"), id=intent_id, organization_id=oid
        )
        if intent.status == PaymentIntentStatus.PENDING:
            intent = maybe_verify_pending_intent(intent)
        return Response(PaymentIntentSerializer(intent).data)


class PaymentIntentCancelView(APIView):
    permission_classes = [HasTenantContext, CanManageBilling]

    def post(self, request, intent_id):
        oid = org_id(request)
        intent = get_object_or_404(PaymentIntent, id=intent_id, organization_id=oid)
        if intent.status not in (PaymentIntentStatus.INITIATED, PaymentIntentStatus.PENDING):
            return Response({"error": "Only pending intents can be cancelled."}, status=status.HTTP_400_BAD_REQUEST)
        intent.status = PaymentIntentStatus.CANCELLED
        intent.save(update_fields=["status", "updated_at"])
        return Response(PaymentIntentSerializer(intent).data)


class PaymentIntentReceiptView(APIView):
    permission_classes = [HasTenantContext, CanManageBilling]

    def get(self, request, intent_id):
        oid = org_id(request)
        intent = get_object_or_404(
            PaymentIntent.objects.select_related("member", "organization"),
            id=intent_id,
            organization_id=oid,
        )
        if intent.status != PaymentIntentStatus.SUCCESS:
            return Response({"error": "Receipt available only for successful payments."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(build_receipt(intent))


class CollectionsStatsView(APIView):
    permission_classes = [HasTenantContext, CanReadBilling]

    def get(self, request):
        oid = org_id(request)
        start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_qs = PaymentIntent.objects.filter(organization_id=oid, created_at__gte=start)
        succeeded = today_qs.filter(status=PaymentIntentStatus.SUCCESS).aggregate(total=Sum("amount_minor"))["total"] or 0
        pending = today_qs.filter(status=PaymentIntentStatus.PENDING).count()
        failed = today_qs.filter(status=PaymentIntentStatus.FAILED).count()
        return Response(
            {
                "collections_today_minor": succeeded,
                "pending_intents": pending,
                "failed_intents": failed,
                "flutterwave_configured": is_flutterwave_configured(),
                "flutterwave_env": __import__("os").getenv("FLUTTERWAVE_ENV", "sandbox"),
            }
        )
