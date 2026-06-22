#!/usr/bin/env python3
"""
Automation agent — PLATINUM tier upgrade via Setup Transfer API.

Usage:
  python scripts/automation_platinum_upgrade.py
  SMOKE_BASE_URL=https://elite-fintech-api-production.up.railway.app python scripts/automation_platinum_upgrade.py

Flow (matches Cursor / CI automation):
  1. Login with org admin JWT
  2. GET /api/v1/platform/setup/
  3. POST /api/v1/platform/setup/apply/ { upgrade_tier: PLATINUM, automation_agent: cursor }
  4. Print deploy_actions for Railway / VPS
  5. Verify capabilities + readiness
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000")
EMAIL = os.getenv("AUTOMATION_EMAIL", "demo@elitefintech.co.ug")
AGENT = os.getenv("AUTOMATION_AGENT", "cursor")


def request(method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.URLError as exc:
        hint = (
            f"Cannot connect to {BASE}. Start the API in another terminal: npm run dev:backend"
            if "refused" in str(exc).lower() or "10061" in str(exc)
            else str(exc)
        )
        return 0, {"error": hint}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"error": raw}
        return exc.code, payload


def _login_body() -> dict[str, str]:
    """Demo credentials match seed_demo — override via AUTOMATION_EMAIL / AUTOMATION_PASSWORD."""
    from smoke_live import DEMO_PASSWORD

    secret = os.getenv("AUTOMATION_PASSWORD", DEMO_PASSWORD)
    return {"email": EMAIL, "password": secret}


def authenticate() -> tuple[str | None, int]:
    status, login = request("POST", "/api/v1/auth/login/", _login_body())
    if status == 0:
        print(f"[FAIL] {login.get('error', login)}")
        return None, 1
    if status != 200:
        print(f"[FAIL] Login -> HTTP {status}: {login}")
        return None, 1
    print("[PASS] Authenticated")
    return login["token"], 0


def fetch_setup(token: str) -> tuple[dict | None, int]:
    status, setup = request("GET", "/api/v1/platform/setup/", token=token)
    if status != 200:
        print(f"[FAIL] GET setup -> HTTP {status}: {setup}")
        return None, 1
    print(f"[PASS] Setup manifest (tier={setup.get('platform_tier')}, readiness={setup.get('readiness_score')})")
    return setup, 0


def apply_platinum(token: str) -> tuple[dict | None, int]:
    status, manifest = request(
        "POST",
        "/api/v1/platform/setup/apply/",
        {
            "upgrade_tier": "PLATINUM",
            "automation_agent": AGENT,
            "completed_steps": ["readiness_check"],
        },
        token=token,
    )
    if status != 200:
        print(f"[FAIL] PLATINUM apply -> HTTP {status}: {manifest}")
        if status == 400 and "upgrade_tier" in str(manifest):
            print("\nHint: Redeploy API with latest code (upgrade_tier support required).")
        return None, 1
    print("[PASS] PLATINUM upgrade manifest received")
    print(f"       Message: {manifest.get('message', '')}")
    readiness = manifest.get("readiness", {})
    print(f"       Readiness: {readiness.get('score')}/100 (eligible={readiness.get('eligible')})")
    return manifest, 0


def print_deploy_actions(manifest: dict) -> None:
    deploy = manifest.get("deploy_actions", {})
    railway = deploy.get("railway")
    if railway:
        print("\n--- Railway variables (apply in dashboard or CLI) ---")
        for key, value in railway.get("variables", {}).items():
            print(f"  {key}={value}")
        if note := railway.get("note"):
            print(f"  ({note})")

    env = manifest.get("environment", {})
    if env:
        print("\n--- Production .env ---")
        for key, value in env.items():
            print(f"{key}={value}")


def verify_endpoints(manifest: dict) -> int:
    verify = manifest.get("deploy_actions", {}).get("verify", {})
    warnings = 0
    for label, url in verify.items():
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                body = json.loads(resp.read().decode())
            tier = body.get("tier") or body.get("platform_tier") or body.get("deployment_tier")
            print(f"\n[PASS] Verify {label} -> tier={tier}")
            if label == "capabilities" and tier != "PLATINUM":
                print("       WARN: PLATFORM_TIER=PLATINUM not live yet — redeploy after setting env vars")
                warnings += 1
        except Exception as exc:
            print(f"\n[WARN] Verify {label} -> {exc}")
            warnings += 1
    return warnings


def main() -> int:
    print("Elite Fintech — PLATINUM automation upgrade")
    print(f"Target: {BASE}")
    print(f"Agent:  {AGENT}\n")

    token, code = authenticate()
    if code:
        return code

    _, code = fetch_setup(token)
    if code:
        return code

    manifest, code = apply_platinum(token)
    if code:
        return code

    print_deploy_actions(manifest)
    warnings = verify_endpoints(manifest)

    print()
    if warnings:
        print("AUTOMATION COMPLETE — apply deploy_actions and redeploy to activate PLATINUM live")
        return 0

    print("AUTOMATION COMPLETE — PLATINUM tier active")
    return 0


if __name__ == "__main__":
    sys.exit(main())
