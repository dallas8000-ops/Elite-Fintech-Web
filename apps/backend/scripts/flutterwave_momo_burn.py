#!/usr/bin/env python3
"""End-to-end Flutterwave MoMo sandbox burn: checkout → phone → OTP → subscription."""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import uuid

BASE = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
DEMO_EMAIL = "demo@elitefintech.co.ug"
DEMO_PASSWORD = "demo1234"
SANDBOX_PHONE = "0700000000"
SANDBOX_OTP = os.getenv("FLUTTERWAVE_SANDBOX_OTP", "123456")


def fetch_html(path: str) -> tuple[int, str]:
    url = f"{BASE}{path}" if path.startswith("/") else path
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()

def request(method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict | str]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    url = f"{BASE}{path}" if path.startswith("/") else path
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            try:
                return resp.status, json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def form_post(path: str, fields: dict[str, str]) -> tuple[int, str]:
    body = urllib.parse.urlencode(fields).encode()
    url = f"{BASE}{path}" if path.startswith("/") else path
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def api_checkout_url(url: str) -> str:
    if url.startswith("/"):
        return f"{BASE}{url}"
    for origin in (
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5177",
        "http://127.0.0.1:5177",
    ):
        if url.startswith(origin):
            return url.replace(origin, BASE, 1)
    return url


def main() -> int:
    print("Flutterwave MoMo BURN TEST")
    print(f"API: {BASE}")

    status, login = request("POST", "/api/v1/auth/login/", {"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    if status != 200:
        print(f"[FAIL] login HTTP {status}: {login}")
        return 1
    token = login.get("access") or login.get("token")
    print("[PASS] login")

    nonce = f"burn-{uuid.uuid4().hex[:10]}"
    status, checkout = request(
        "POST",
        "/api/v1/billing/checkout/",
        {"tier": "PRO", "rail": "MOBILE_MONEY", "client_nonce": nonce},
        token=token,
    )
    if status != 200:
        print(f"[FAIL] checkout HTTP {status}: {checkout}")
        return 1
    pay_url = checkout.get("url", "")
    tx_ref = checkout.get("tx_ref", "")
    if checkout.get("provider") != "FLUTTERWAVE" or not pay_url:
        print(f"[FAIL] checkout payload: {checkout}")
        return 1
    print(f"[PASS] checkout tx_ref={tx_ref}")

    parsed = urllib.parse.urlparse(api_checkout_url(pay_url))
    query = urllib.parse.parse_qs(parsed.query)
    session_id = (query.get("session") or [""])[0]
    org_id = (query.get("org") or [""])[0]
    tier = (query.get("tier") or ["PRO"])[0]
    rail = (query.get("rail") or ["MOBILE_MONEY"])[0]
    country = (query.get("country") or ["UG"])[0]
    if not session_id:
        print(f"[FAIL] missing session in pay URL: {pay_url}")
        return 1

    status, html = fetch_html(parsed.path + "?" + parsed.query)
    if status != 200 or "Pay with Mobile Money" not in html:
        print(f"[FAIL] MoMo pay form HTTP {status}")
        return 1
    print("[PASS] MoMo pay form")

    status, post_html = form_post(
        "/billing/flutterwave/pay/",
        {
            "session": session_id,
            "phone": SANDBOX_PHONE,
            "rail": rail,
            "country": country,
            "tier": tier,
            "org": org_id,
            "network": "MTN",
        },
    )
    if status != 200:
        print(f"[FAIL] MoMo charge HTTP {status}")
        if "error" in post_html.lower():
            print(post_html[:500])
        return 1

    if "Payment confirmed" in post_html:
        print("[PASS] MoMo charge auto-confirmed (sandbox OTP)")
        activated = True
        charge_id = ""
        amount = ""
    elif "MoMo prompt sent" not in post_html:
        print("[FAIL] MoMo charge unexpected response")
        print(post_html[:500])
        return 1
    else:
        charge_match = re.search(r'name="charge" value="([^"]+)"', post_html)
        amount_match = re.search(r'name="amount" value="(\d+)"', post_html)
        if not charge_match:
            print("[FAIL] charge id not found in response")
            return 1
        charge_id = charge_match.group(1)
        amount = amount_match.group(1) if amount_match else ""
        print(f"[PASS] MoMo prompt charge={charge_id}")
        activated = False

        for attempt in range(15):
            time.sleep(2)
            q = urllib.parse.urlencode(
                {
                    "charge": charge_id,
                    "tx_ref": tx_ref,
                    "org": org_id,
                    "tier": tier,
                    "rail": rail,
                    "amount": amount,
                }
            )
            status, result = request("GET", f"/billing/flutterwave/pay/status/?{q}")
            if status == 200 and isinstance(result, dict) and result.get("activated"):
                activated = True
                print(f"[PASS] subscription activated after poll {attempt + 1}")
                break
            if isinstance(result, dict):
                print(f"  poll {attempt + 1}: status={result.get('status')} otp={result.get('requires_otp')}")

        if not activated:
            print("[WARN] polling did not activate — trying OTP form")
            status, otp_html = form_post(
                "/billing/flutterwave/pay/otp/",
                {
                    "charge": charge_id,
                    "session": session_id,
                    "tx_ref": tx_ref,
                    "org": org_id,
                    "tier": tier,
                    "rail": rail,
                    "amount": amount,
                    "otp": SANDBOX_OTP,
                    "redirect_url": "http://localhost:5175/dashboard",
                },
            )
            if status == 200 and "Payment confirmed" in otp_html:
                activated = True
                print("[PASS] OTP confirmation page")

    status, sub = request("GET", "/api/v1/billing/subscription/", token=token)
    tier_now = ""
    if status == 200 and isinstance(sub, dict):
        sub_data = sub.get("subscription") or sub
        tier_now = sub_data.get("planTier") or sub_data.get("plan_tier") or sub_data.get("tier", "")
    if activated and tier_now == "PRO":
        print(f"[PASS] dashboard subscription tier=PRO")
        print("\nFLUTTERWAVE MOMO BURN TEST PASSED")
        return 0

    print(f"[FAIL] activated={activated} subscription_tier={tier_now or 'unknown'}")
    print("\nFLUTTERWAVE MOMO BURN TEST FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
