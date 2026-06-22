import os

from django.http import JsonResponse
from django.urls import path

from config.readiness import deployment_tier_for_score, readiness_score, readiness_summary, run_readiness_checks


def health(_request):
    payload = {
        "status": "ok",
        "service": "elite-fintech-api",
        "version": "1.0.0",
    }
    try:
        from billing.services.regional import market_summary

        summary = market_summary()
        payload["market"] = summary["market"]
        payload["region"] = summary.get("label", "East Africa")
    except Exception:
        payload["market"] = "EA"
        payload["region"] = "East Africa"

    checks = run_readiness_checks()
    payload["checks"] = {c["id"]: "ok" if c["passed"] else "fail" for c in checks}
    payload["readiness_score"] = readiness_score(checks)
    payload["deployment_tier"] = deployment_tier_for_score(payload["readiness_score"])

    if os.getenv("RAILWAY_ENVIRONMENT"):
        payload["platform"] = "railway"

    critical_failed = any(not c["passed"] for c in checks if c["id"] in ("database", "health_endpoint"))
    if critical_failed:
        payload["status"] = "degraded"
        return JsonResponse(payload, status=503)

    return JsonResponse(payload)


def readiness(_request):
    return JsonResponse(readiness_summary())


urlpatterns = [
    path("", health, name="health"),
    path("ready/", readiness, name="readiness"),
]
