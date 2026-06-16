#!/usr/bin/env python3
"""
Live API smoke test against a running Django server.

Usage (from repo root):
  npm run dev:backend   # terminal 1
  npm run smoke         # terminal 2 — seeds demo data then hits the API
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000")
DEMO_EMAIL = "demo@elitefintech.co.ug"
DEMO_PASSWORD = "demo1234"


def request(method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"error": raw}
        return exc.code, payload


def check(name: str, status: int, expected: int, payload: dict) -> bool:
    ok = status == expected
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {name} -> HTTP {status}")
    if not ok:
        print(f"         {payload}")
    return ok


def main() -> int:
    print("Elite Fintech Systems — live smoke test")
    print(f"Target: {BASE}\n")
    failed = 0

    try:
        urllib.request.urlopen(f"{BASE}/health/", timeout=5)
        print("  [PASS] GET /health/")
    except Exception as exc:
        print(f"  [FAIL] GET /health/ -> {exc}")
        print("\nStart the API first: npm run dev:backend")
        return 1

    status, login = request("POST", "/api/v1/auth/login/", {"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    if not check("POST /api/v1/auth/login/ (demo user)", status, 200, login):
        return 1
    token = login["token"]

    for method, path, expected in [
        ("GET", "/api/v1/auth/me/", 200),
        ("GET", "/api/v1/billing/stats/", 200),
        ("GET", "/api/v1/billing/events/", 200),
        ("GET", "/api/v1/billing/plans/", 200),
        ("GET", "/api/v1/billing/rails/", 200),
        ("GET", "/api/v1/org/", 200),
        ("GET", "/api/v1/org/members/", 200),
    ]:
        status, payload = request(method, path, token=token)
        if not check(f"{method} {path}", status, expected, payload):
            failed += 1

    status, patched = request(
        "PATCH",
        "/api/v1/org/",
        {"industry_sector": "Payments & Wallets"},
        token=token,
    )
    if not check("PATCH /api/v1/org/ (settings)", status, 200, patched):
        failed += 1
    elif patched.get("organization", {}).get("industry_sector") != "Payments & Wallets":
        print("  [FAIL] PATCH /api/v1/org/ -> industry_sector not updated")
        failed += 1

    status, events = request("GET", "/api/v1/billing/events/", token=token)
    if status == 200:
        count = len(events.get("events", []))
        if count >= 1:
            print(f"  [PASS] simulated MoMo events present ({count} rows)")
        else:
            print("  [WARN] no payment events in DB — run: npm run seed")

    print()
    if failed:
        print(f"SMOKE TEST FAILED ({failed} check(s))")
        return 1

    print("ALL SMOKE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
