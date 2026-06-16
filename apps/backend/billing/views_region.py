from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.services.regional import market_summary, registration_labels, region_choices
from billing.services.fx_rates import rates_public_payload


class FxRatesView(APIView):
    """Public — latest daily FX snapshot used for plan pricing."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(rates_public_payload())


class RegionConfigView(APIView):
    """Public — East Africa markets, pricing tiers, registration fields."""

    permission_classes = [AllowAny]

    def get(self, request):
        country = request.query_params.get("country")
        labels = registration_labels(country)
        return Response(
            {
                **market_summary(),
                "registration": labels,
                "regions": [{"value": k, "label": v} for k, v in region_choices(country)],
            }
        )
