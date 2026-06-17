import json
import logging

from django.db import transaction
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView

from sacco.models import PaymentIntent, PaymentIntentStatus
from sacco.services.intents import complete_intent_failed, complete_intent_success
from sacco.services.payments.flutterwave import verify_webhook_signature

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class FlutterwaveWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    @transaction.atomic
    def post(self, request):
        body = request.body
        signature = request.headers.get("verif-hash")
        if not verify_webhook_signature(body, signature):
            logger.warning("Flutterwave webhook rejected: invalid signature")
            return HttpResponse("Invalid signature", status=400)

        try:
            payload = json.loads(body.decode())
        except json.JSONDecodeError:
            return HttpResponse("Invalid JSON", status=400)

        event_type = payload.get("event") or payload.get("eventType") or ""
        data = payload.get("data") or payload
        tx_ref = data.get("tx_ref") or data.get("txRef") or ""
        flw_id = str(data.get("id") or data.get("transaction_id") or "")
        status_value = (data.get("status") or "").lower()

        if not tx_ref:
            return HttpResponse("OK")

        intent = PaymentIntent.objects.filter(provider_reference=tx_ref).select_related("member", "organization").first()
        if not intent:
            logger.warning("Flutterwave webhook: unknown tx_ref %s", tx_ref)
            return HttpResponse("OK")

        if event_type == "charge.completed" or status_value == "successful":
            complete_intent_success(intent, provider_transaction_id=flw_id or intent.provider_transaction_id, raw=payload)
        elif status_value in ("failed", "cancelled") or event_type.endswith("failed"):
            complete_intent_failed(intent, reason=status_value or event_type, raw=payload)
        elif intent.status == PaymentIntentStatus.PENDING and status_value:
            logger.info("Flutterwave webhook intermediate status %s for %s", status_value, tx_ref)

        return HttpResponse("OK")
