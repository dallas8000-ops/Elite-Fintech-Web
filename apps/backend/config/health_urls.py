from django.http import JsonResponse
from django.urls import path


def health(_request):
    payload = {"status": "ok", "service": "elite-fintech-api"}
    try:
        from billing.services.regional import market_summary

        summary = market_summary()
        payload["market"] = summary["market"]
        payload["region"] = summary.get("label", "East Africa")
    except Exception:
        payload["market"] = "EA"
        payload["region"] = "East Africa"
    return JsonResponse(payload)


urlpatterns = [path("", health, name="health")]
