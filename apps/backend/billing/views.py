from datetime import datetime, timedelta, timezone
import logging

from django.db.models import Sum

from django.shortcuts import get_object_or_404

from rest_framework import status

from rest_framework.response import Response

from rest_framework.views import APIView



from accounts.permissions import CanManageBilling, CanReadBilling, HasTenantContext

from billing.models import PaymentEvent, PaymentEventType, PaymentProvider, Subscription, SubscriptionStatus

from billing.serializers import CheckoutSerializer, PaymentEventSerializer, SubscriptionSerializer

from billing.services.african_payments import MARKET_CONTEXT, rails_for_checkout, resolve_checkout

from billing.services.payfast import create_payfast_checkout_url, is_payfast_configured

from billing.services.fx_rates import rates_public_payload
from billing.services.plans import get_available_plans

from billing.services.regional import (

    default_currency,

    extract_vat_from_inclusive,

    is_east_africa,

    is_south_africa,

    plan_by_tier,

)

from billing.services.stripe_service import get_stripe_client, is_stripe_configured

from django.conf import settings

from organizations.models import Organization

import os

logger = logging.getLogger(__name__)




def org_id(request) -> str:

    return request.auth.payload["organization_id"]





def org_country(request) -> str:

    org = Organization.objects.filter(id=org_id(request)).only("country").first()

    return org.country if org else "UG"





class PlansView(APIView):

    permission_classes = [HasTenantContext, CanReadBilling]



    def get(self, request):

        country = request.query_params.get("country") or org_country(request)

        return Response(

            {

                "market": "EA" if is_east_africa() else "ZA",

                "country": country,

                "currency": default_currency(country),

                "pricing": rates_public_payload(),

                "plans": get_available_plans(country),

            }

        )





class RailsView(APIView):

    permission_classes = [HasTenantContext, CanReadBilling]



    def get(self, request):

        philosophy = (

            "East Africa billing routes by mobile money, USSD, and agents — not US card-on-file. "

            "Settlement is wallet-native; Flutterwave/Pesapal aggregate MoMo across UG, KE, RW, TZ."

            if is_east_africa()

            else "South Africa legacy rails — bank EFT, PayShap, DebiCheck."

        )

        return Response(

            {

                "rails": rails_for_checkout(),

                "markets": MARKET_CONTEXT,

                "philosophy": philosophy,

            }

        )





class SubscriptionView(APIView):

    permission_classes = [HasTenantContext, CanReadBilling]



    def get(self, request):

        sub = Subscription.objects.filter(organization_id=org_id(request)).first()

        return Response({"subscription": SubscriptionSerializer(sub).data if sub else None})





class EventsView(APIView):

    permission_classes = [HasTenantContext, CanReadBilling]



    def get(self, request):

        limit = min(int(request.query_params.get("limit", 50)), 100)

        events = PaymentEvent.objects.filter(organization_id=org_id(request))[:limit]

        return Response({"events": PaymentEventSerializer(events, many=True).data})





class StatsView(APIView):

    permission_classes = [HasTenantContext, CanReadBilling]



    def get(self, request):

        oid = org_id(request)

        country = org_country(request)

        sub = Subscription.objects.filter(organization_id=oid).first()

        event_count = PaymentEvent.objects.filter(organization_id=oid).count()

        revenue = (

            PaymentEvent.objects.filter(organization_id=oid, type=PaymentEventType.INVOICE_PAID)

            .aggregate(total=Sum("amount"))

            .get("total")

            or 0

        )

        from sacco.models import PaymentIntent, PaymentIntentStatus

        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_intents = PaymentIntent.objects.filter(organization_id=oid, created_at__gte=start)
        collections_today = (
            today_intents.filter(status=PaymentIntentStatus.SUCCESS).aggregate(total=Sum("amount_minor")).get("total")
            or 0
        )
        pending_intents = today_intents.filter(status=PaymentIntentStatus.PENDING).count()
        failed_intents = today_intents.filter(status=PaymentIntentStatus.FAILED).count()

        return Response(

            {

                "subscription": SubscriptionSerializer(sub).data if sub else None,

                "totalEvents": event_count,

                "totalRevenue": revenue,

                "currency": default_currency(country),

                "country": country,

                "collections_today_minor": collections_today,

                "pending_intents": pending_intents,

                "failed_intents": failed_intents,

            }

        )





class CheckoutView(APIView):

    permission_classes = [HasTenantContext, CanManageBilling]
    throttle_scope = "billing-checkout"



    def post(self, request):

        serializer = CheckoutSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        org = get_object_or_404(Organization, id=org_id(request))

        plan = plan_by_tier(data["tier"], org.country)

        if not plan:

            return Response({"error": "Invalid plan tier"}, status=status.HTTP_400_BAD_REQUEST)



        rail = data["rail"]

        try:

            _, provider = resolve_checkout(rail, data.get("provider"))

        except ValueError as exc:

            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)



        if provider == "STRIPE" or (rail == "CARD" and data.get("provider") == "STRIPE"):

            client = get_stripe_client()

            if not client:

                return Response(

                    {"error": "Stripe not configured. Use mobile money rails for East Africa."},

                    status=status.HTTP_503_SERVICE_UNAVAILABLE,

                )

            price_map = {

                "STARTER": settings.STRIPE_PRICE_STARTER,

                "PRO": settings.STRIPE_PRICE_PRO,

                "ENTERPRISE": settings.STRIPE_PRICE_ENTERPRISE,

            }

            price_id = price_map.get(data["tier"], "")

            nonce = data.get("client_nonce") or f"{org.id}:{data['tier']}:{rail}"
            customer_idempotency_key = f"efs-customer-{org.id}"
            session_idempotency_key = f"efs-checkout-{org.id}-{data['tier']}-{rail}-{nonce}"

            try:
                if not org.stripe_customer_id:
                    customer = client.customers.create(
                        params={
                            "email": request.user.email,
                            "name": org.name,
                            "metadata": {"organization_id": str(org.id), "country": org.country},
                        },
                        options={"idempotency_key": customer_idempotency_key},
                    )

                    org.stripe_customer_id = customer.id
                    org.save(update_fields=["stripe_customer_id"])

                session = client.checkout.sessions.create(
                    params={
                        "customer": org.stripe_customer_id,
                        "mode": "subscription",
                        "line_items": [{"price": price_id, "quantity": 1}],
                        "success_url": f"{settings.CLIENT_URL}/dashboard?checkout=success&rail={rail}",
                        "cancel_url": f"{settings.CLIENT_URL}/dashboard?checkout=canceled",
                        "metadata": {"organization_id": str(org.id), "rail": rail, "country": org.country},
                        "subscription_data": {"metadata": {"organization_id": str(org.id)}},
                    },
                    options={"idempotency_key": session_idempotency_key},
                )
            except Exception as exc:
                logger.warning("Stripe checkout failed for org %s: %s", org.id, exc)
                return Response(
                    {"error": "Stripe checkout unavailable. Verify Stripe credentials and retry."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            return Response({"url": session.url, "provider": "STRIPE", "rail": rail})



        if is_east_africa():

            if not os.getenv("FLUTTERWAVE_SECRET_KEY"):

                return Response(

                    {

                        "error": (

                            "Flutterwave not configured. Add FLUTTERWAVE_SECRET_KEY for "

                            f"MoMo checkout ({org.country})."

                        ),

                        "rail": rail,

                        "provider": "FLUTTERWAVE",

                    },

                    status=status.HTTP_503_SERVICE_UNAVAILABLE,

                )

            return Response(

                {

                    "error": "Flutterwave checkout integration pending — configure webhook + payment link API.",

                    "rail": rail,

                    "provider": "FLUTTERWAVE",

                    "country": org.country,

                },

                status=status.HTTP_501_NOT_IMPLEMENTED,

            )



        if not is_payfast_configured():

            return Response(

                {"error": "PayFast not configured (South Africa legacy market only)."},

                status=status.HTTP_503_SERVICE_UNAVAILABLE,

            )



        if rail in ("PAYSHAP", "RNCS") and data.get("provider") in ("PEACH_PAYMENTS", "OZOW"):

            return Response(

                {"error": f"{rail} requires PSP credentials in .env.", "rail": rail},

                status=status.HTTP_501_NOT_IMPLEMENTED,

            )



        url, payment_id = create_payfast_checkout_url(

            organization_id=str(org.id),

            plan=plan,

            customer_email=request.user.email,

            customer_name=request.user.name,

            return_url=f"{settings.CLIENT_URL}/dashboard?checkout=success&rail={rail}",

            cancel_url=f"{settings.CLIENT_URL}/dashboard?checkout=canceled",

            notify_url=request.build_absolute_uri("/webhooks/payfast/"),

            rail=rail,

        )

        return Response(

            {

                "url": url,

                "provider": "PAYFAST",

                "rail": rail,

                "payment_id": payment_id,

                "settlement_note": "Instant EFT or debit order — SA legacy market.",

            }

        )





class PortalView(APIView):

    permission_classes = [HasTenantContext, CanManageBilling]



    def post(self, request):

        org = get_object_or_404(Organization, id=org_id(request))

        client = get_stripe_client()

        if not client or not org.stripe_customer_id:

            return Response(

                {

                    "error": (

                        "No card billing portal — East Africa subscriptions use mobile money "

                        "mandates via Flutterwave/Pesapal, not US-style portals."

                    ),

                },

                status=status.HTTP_400_BAD_REQUEST,

            )

        session = client.billing_portal.sessions.create(

            params={

                "customer": org.stripe_customer_id,

                "return_url": f"{settings.CLIENT_URL}/dashboard",

            }

        )

        return Response({"url": session.url})


