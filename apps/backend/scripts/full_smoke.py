#!/usr/bin/env python3
"""
Full live smoke test for Elite Fintech Systems.

Exercises auth, billing, collections, org, platform, webhooks, and Flutterwave
checkout against a running Django server.

Usage:
  SMOKE_BASE_URL=http://127.0.0.1:8001 python scripts/full_smoke.py
  SMOKE_FRONTEND_URL=http://localhost:5175 python scripts/full_smoke.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field

BASE = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
FRONTEND = os.getenv("SMOKE_FRONTEND_URL", "http://localhost:5175").rstrip("/")
DEMO_EMAIL = "demo@elitefintech.co.ug"
DEMO_PASSWORD = "demo1234"


@dataclass
class Suite:
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    failures: list[str] = field(default_factory=list)

    def ok(self, name: str, detail: str = "") -> None:
        self.passed += 1
        suffix = f" — {detail}" if detail else ""
        print(f"  [PASS] {name}{suffix}")

    def fail(self, name: str, detail: str) -> None:
        self.failed += 1
        self.failures.append(f"{name}: {detail}")
        print(f"  [FAIL] {name} -> {detail}")

    def warn(self, name: str, detail: str) -> None:
        self.warnings += 1
        print(f"  [WARN] {name} -> {detail}")


def request(
    method: str,
    path: str,
    body: dict | None = None,
    token: str | None = None,
    *,
    base: str = BASE,
    expect_json: bool = True,
    retries: int = 3,
) -> tuple[int, dict | str]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    url = f"{base}{path}" if path.startswith("/") else path

    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode()
                if not expect_json:
                    return resp.status, raw
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode()
            if exc.code == 429 and attempt < retries - 1:
                wait = 12
                if "Expected available in" in raw:
                    try:
                        wait = int(raw.split("Expected available in")[1].split("second")[0].strip()) + 1
                    except ValueError:
                        pass
                time.sleep(wait)
                continue
            if not expect_json:
                return exc.code, raw
            try:
                return exc.code, json.loads(raw)
            except json.JSONDecodeError:
                return exc.code, {"error": raw}
    return 429, {"error": "rate limited"}


def fetch_html(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def _api_pay_url(checkout_url: str) -> str:
    """Resolve checkout URL to the Django API origin for pay-bridge HTML tests."""
    if checkout_url.startswith("/"):
        return f"{BASE}{checkout_url}"
    for origin in (FRONTEND, "http://localhost:5175", "http://127.0.0.1:5175",
                   "http://localhost:5173", "http://127.0.0.1:5173",
                   "http://localhost:5177", "http://127.0.0.1:5177"):
        if checkout_url.startswith(origin):
            return checkout_url.replace(origin, BASE, 1)
def section(title: str) -> None:
    print(f"\n== {title} ==")


def main() -> int:
    suite = Suite()
    print("Elite Fintech Systems — FULL SMOKE TEST")
    print(f"API:      {BASE}")
    print(f"Frontend: {FRONTEND}")

    # --- Infrastructure ---
    section("Infrastructure")
    try:
        status, health = request("GET", "/health/")
        if status == 200 and health.get("status") in ("ok", "degraded"):
            suite.ok("GET /health/", f"market={health.get('market')} score={health.get('readiness_score')}")
        else:
            suite.fail("GET /health/", f"HTTP {status} {health}")
    except Exception as exc:
        suite.fail("GET /health/", str(exc))
        print("\nStart API: cd apps/backend && .venv\\Scripts\\python.exe manage.py runserver 8001")
        return 1

    status, ready = request("GET", "/health/ready/")
    if status in (200, 503) and isinstance(ready, dict) and "checks" in ready:
        suite.ok("GET /health/ready/", f"HTTP {status}")
    else:
        suite.fail("GET /health/ready/", f"HTTP {status}")

    # --- Auth ---
    section("Authentication")
    status, bad_login = request("POST", "/api/v1/auth/login/", {"email": DEMO_EMAIL, "password": "wrong"})
    if status in (400, 401):
        suite.ok("POST /api/v1/auth/login/ rejects bad password", f"HTTP {status}")
    else:
        suite.fail("POST /api/v1/auth/login/ rejects bad password", f"HTTP {status}")

    status, login = request("POST", "/api/v1/auth/login/", {"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    if status != 200:
        suite.fail("POST /api/v1/auth/login/", f"HTTP {status} {login}")
        return 1
    token = login.get("access") or login.get("token")
    if not token:
        suite.fail("POST /api/v1/auth/login/", "missing token")
        return 1
    suite.ok("POST /api/v1/auth/login/", f"role={login.get('role')}")

    status, me = request("GET", "/api/v1/auth/me/", token=token)
    if status == 200 and me.get("user", {}).get("email") == DEMO_EMAIL:
        suite.ok("GET /api/v1/auth/me/")
    else:
        suite.fail("GET /api/v1/auth/me/", f"HTTP {status}")

    status, unauth = request("GET", "/api/v1/billing/stats/")
    if status in (401, 403):
        suite.ok("Protected route requires auth", f"HTTP {status}")
    else:
        suite.fail("Protected route requires auth", f"HTTP {status}")

    # --- Billing read APIs ---
    section("Billing — read APIs")
    billing_reads = [
        ("/api/v1/billing/region/", {"market"}),
        ("/api/v1/billing/rates/", set()),
        ("/api/v1/billing/plans/", set()),
        ("/api/v1/billing/rails/", {"rails"}),
        ("/api/v1/billing/stats/", {"currency"}),
        ("/api/v1/billing/events/", {"events"}),
        ("/api/v1/billing/subscription/", set()),
    ]
    plans_payload: dict = {}
    for path, required_keys in billing_reads:
        status, payload = request("GET", path, token=token)
        if status != 200:
            suite.fail(f"GET {path}", f"HTTP {status}")
            continue
        if path.endswith("/plans/"):
            plans_payload = payload
            plans = payload.get("plans") or payload if isinstance(payload, list) else []
            if isinstance(payload, dict):
                plans = payload.get("plans", [])
            if not plans:
                suite.fail(f"GET {path}", "no plans returned")
            else:
                tiers = {p.get("tier") for p in plans}
                if {"STARTER", "PRO", "ENTERPRISE"}.issubset(tiers):
                    suite.ok(f"GET {path}", f"{len(plans)} plans")
                else:
                    suite.fail(f"GET {path}", f"missing tiers: {tiers}")
        elif required_keys and not required_keys.issubset(payload.keys() if isinstance(payload, dict) else {}):
            suite.fail(f"GET {path}", f"missing keys {required_keys - set(payload.keys())}")
        else:
            suite.ok(f"GET {path}")

    status, region = request("GET", "/api/v1/billing/region/", token=token)
    if status == 200 and region.get("market") == "EA":
        suite.ok("East Africa market config", region.get("label", "EA"))
    else:
        suite.fail("East Africa market config", str(region))

    status, events = request("GET", "/api/v1/billing/events/", token=token)
    event_count = len(events.get("events", [])) if status == 200 else 0
    if event_count >= 1:
        suite.ok("Demo payment events seeded", f"{event_count} events")
    else:
        suite.warn("Demo payment events seeded", "run: python manage.py seed_demo")

    # --- Organization ---
    section("Organization")
    for path in ("/api/v1/org/", "/api/v1/org/members/"):
        status, payload = request("GET", path, token=token)
        if status == 200:
            suite.ok(f"GET {path}")
        else:
            suite.fail(f"GET {path}", f"HTTP {status}")

    status, patched = request(
        "PATCH",
        "/api/v1/org/",
        {"industry_sector": "Payments & Wallets"},
        token=token,
    )
    org = patched.get("organization", patched) if isinstance(patched, dict) else {}
    if status == 200 and org.get("industry_sector") == "Payments & Wallets":
        suite.ok("PATCH /api/v1/org/")
    else:
        suite.fail("PATCH /api/v1/org/", f"HTTP {status}")

    # --- Collections & members ---
    section("Collections & SACCO members")
    collection_reads = [
        "/api/v1/collections/stats/",
        "/api/v1/collections/products/",
        "/api/v1/collections/intents/",
        "/api/v1/members/",
    ]
    for path in collection_reads:
        status, payload = request("GET", path, token=token)
        if status != 200:
            suite.fail(f"GET {path}", f"HTTP {status}")
            continue
        if path.endswith("/stats/") and not payload.get("flutterwave_configured"):
            suite.warn(f"GET {path}", "flutterwave_configured=false")
        else:
            detail = ""
            if path.endswith("/stats/"):
                detail = f"fw={payload.get('flutterwave_configured')}"
            suite.ok(f"GET {path}", detail)

    # --- Platform ---
    section("Platform")
    for path in ("/api/v1/platform/capabilities/", "/api/v1/platform/readiness/", "/api/v1/platform/openapi/"):
        status, payload = request("GET", path, token=token)
        if status == 200:
            suite.ok(f"GET {path}")
        else:
            suite.fail(f"GET {path}", f"HTTP {status}")

    # --- Flutterwave checkout (all tiers × rails) ---
    section("Flutterwave subscription checkout")
    tiers = ("STARTER", "PRO", "ENTERPRISE")
    rails = ("MOBILE_MONEY", "USSD", "CARD")
    checkout_urls: list[str] = []
    tx_refs: list[str] = []

    for tier in tiers:
        for rail in rails:
            nonce = f"smoke-{uuid.uuid4().hex[:12]}"
            status, payload = request(
                "POST",
                "/api/v1/billing/checkout/",
                {"tier": tier, "rail": rail, "client_nonce": nonce},
                token=token,
            )
            if status != 200:
                suite.fail(f"checkout {tier}/{rail}", f"HTTP {status} {payload}")
                continue
            time.sleep(0.75)
            url = payload.get("url", "")
            tx_ref = payload.get("tx_ref", "")
            provider = payload.get("provider", "")
            if not url:
                suite.fail(f"checkout {tier}/{rail}", "missing url")
                continue
            if provider != "FLUTTERWAVE":
                suite.fail(f"checkout {tier}/{rail}", f"provider={provider}")
                continue
            if tx_ref in tx_refs:
                suite.fail(f"checkout {tier}/{rail}", f"duplicate tx_ref {tx_ref}")
            else:
                tx_refs.append(tx_ref)
            checkout_urls.append(url)
            suite.ok(f"checkout {tier}/{rail}", tx_ref)

    # Duplicate-click resilience (unique refs)
    refs: list[str] = []
    for _ in range(3):
        status, payload = request(
            "POST",
            "/api/v1/billing/checkout/",
            {"tier": "PRO", "rail": "MOBILE_MONEY", "client_nonce": uuid.uuid4().hex},
            token=token,
        )
        if status == 200 and payload.get("tx_ref"):
            refs.append(payload["tx_ref"])
        time.sleep(0.75)
    if len(refs) == 3 and len(set(refs)) == 3:
        suite.ok("Repeated PRO/MoMo checkouts use unique references", f"{len(refs)} unique")
    else:
        suite.fail("Repeated PRO/MoMo checkouts", f"refs={refs}")

    # --- MoMo pay bridge page ---
    section("Flutterwave MoMo pay bridge")
    momo_urls = [u for u in checkout_urls if "MOBILE_MONEY" in u or "rail=MOBILE_MONEY" in u]
    if not momo_urls:
        suite.fail("MoMo pay bridge", "no MoMo checkout URL captured")
    else:
        pay_url = momo_urls[0]
        if pay_url.startswith("/"):
            pay_url = f"{FRONTEND}{pay_url}"
        elif pay_url.startswith("http://127.0.0.1:8001"):
            pay_url = pay_url.replace("http://127.0.0.1:8001", FRONTEND, 1)
        elif pay_url.startswith("http://localhost:8001"):
            pay_url = pay_url.replace("http://localhost:8001", FRONTEND, 1)

        # API-origin page (always hit Django, not Vite/Studio on another port)
        api_pay = _api_pay_url(momo_urls[0])
        status, html = fetch_html(api_pay)
        if (
            status == 200
            and "Pay with Mobile Money" in html
            and 'name="phone"' in html
            and 'action="https://checkout.flutterwave.com' not in html
        ):
            suite.ok("MoMo pay page (API)", "phone form, no v3 auto-post")
        else:
            suite.fail("MoMo pay page (API)", f"HTTP {status}")

        # Frontend proxy page (optional)
        try:
            fstatus, fhtml = fetch_html(pay_url)
            if fstatus == 200 and "Pay with Mobile Money" in fhtml:
                suite.ok("MoMo pay page (Vite proxy)", pay_url[:60])
            else:
                suite.warn("MoMo pay page (Vite proxy)", f"HTTP {fstatus} — is npm run dev running on {FRONTEND}?")
        except Exception as exc:
            suite.warn("MoMo pay page (Vite proxy)", str(exc))

    # --- Webhook endpoints ---
    section("Webhook endpoints")
    for path, expected in (
        ("/webhooks/flutterwave/", (400, 401, 403)),
        ("/webhooks/stripe/", (400, 401, 403)),
        ("/webhooks/payfast/", (400, 401, 403, 405)),
    ):
        status, _ = request("POST", path, {})
        if status in expected:
            suite.ok(f"POST {path}", f"HTTP {status}")
        else:
            suite.fail(f"POST {path}", f"HTTP {status} expected one of {expected}")

    # --- Frontend dashboard (optional) ---
    section("Frontend")
    try:
        status, html = fetch_html(f"{FRONTEND}/dashboard")
        if status == 200 and ("Subscribe by payment rail" in html or "id=\"root\"" in html or '<div id="root">' in html):
            suite.ok("Frontend dashboard reachable", FRONTEND)
        else:
            suite.warn("Frontend dashboard", f"HTTP {status}")
    except Exception as exc:
        suite.warn("Frontend dashboard", f"{exc}")

    # --- Summary ---
    print("\n" + "=" * 60)
    print(f"PASSED:   {suite.passed}")
    print(f"FAILED:   {suite.failed}")
    print(f"WARNINGS: {suite.warnings}")
    if suite.failures:
        print("\nFailures:")
        for item in suite.failures:
            print(f"  • {item}")
    print("=" * 60)

    if suite.failed:
        print("FULL SMOKE TEST FAILED")
        return 1
    print("FULL SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
