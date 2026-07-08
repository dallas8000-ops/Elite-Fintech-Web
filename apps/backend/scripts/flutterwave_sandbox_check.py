"""Verify Flutterwave sandbox configuration and optionally create a test payment link."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import django

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))
os.chdir(BACKEND_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from sacco.services.payments.flutterwave import flutterwave_env, is_flutterwave_configured  # noqa: E402


def main() -> int:
    print("Flutterwave sandbox check")
    print(f"  FLUTTERWAVE_ENV={flutterwave_env()}")
    print(f"  configured={is_flutterwave_configured()}")

    secret = os.getenv("FLUTTERWAVE_SECRET_KEY", "").strip()
    client_id = os.getenv("FLUTTERWAVE_CLIENT_ID", "").strip()
    client_secret = os.getenv("FLUTTERWAVE_CLIENT_SECRET", "").strip()
    if not secret and not (client_id and client_secret):
        print("\nMissing Flutterwave credentials in apps/backend/.env")
        print("v4 sandbox dashboard: paste Client ID + Client Secret")
        print("  FLUTTERWAVE_CLIENT_ID=...")
        print("  FLUTTERWAVE_CLIENT_SECRET=...")
        print("Legacy v3 keys also work:")
        print("  FLUTTERWAVE_SECRET_KEY=FLWSECK_TEST-...")
        return 1

    from billing.services.flutterwave_checkout import create_flutterwave_subscription_checkout
    from billing.services.regional import plan_by_tier
    from organizations.models import Organization

    org = Organization.objects.filter(country="UG").first()
    if not org:
        print("\nNo UG organization in database — run: python manage.py seed_demo")
        return 1

    plan = plan_by_tier("STARTER", org.country)
    if not plan:
        print("\nNo STARTER plan for UG")
        return 1

    import uuid

    try:
        result = create_flutterwave_subscription_checkout(
            organization=org,
            tier="STARTER",
            rail="MOBILE_MONEY",
            email="sandbox@elitefintech.co.ug",
            plan=plan,
            client_nonce=f"sandbox-smoke-{uuid.uuid4().hex[:8]}",
        )
    except Exception as exc:
        print(f"\nFlutterwave API error: {exc}")
        return 1

    print("\nSandbox payment link created:")
    print(json.dumps(result, indent=2))
    print("\nOpen the URL in a browser to complete Flutterwave test checkout.")
    print("Webhook endpoint (configure in Flutterwave dashboard):")
    print("  http://127.0.0.1:8001/webhooks/flutterwave/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
