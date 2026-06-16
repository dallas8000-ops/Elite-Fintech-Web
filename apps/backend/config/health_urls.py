from django.http import JsonResponse
from django.urls import path


def health(_request):
    from billing.services.regional import market_summary

    summary = market_summary()
    return JsonResponse(
        {
            "status": "ok",
            "service": "elite-fintech-api",
            "market": summary["market"],
            "region": summary.get("label", "East Africa"),
        }
    )


urlpatterns = [path("", health, name="health")]
