#!/usr/bin/env python3
"""
Elite Fintech Systems — automated self-check.

Runs offline validation (always) and optional live API smoke (when API is up).

Usage:
  npm run check              # migrate + django check + tests + contract checks
  npm run check:live         # above + seed + live HTTP smoke (needs runserver)
  python scripts/self_check.py --live

Exit code 0 = all checks passed. Non-zero = fix before shipping.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent


def _run(cmd: list[str], label: str) -> bool:
    print(f"\n--- {label} ---")
    result = subprocess.run(cmd, cwd=BACKEND_DIR)
    if result.returncode != 0:
        print(f"[FAIL] {label}")
        return False
    print(f"[PASS] {label}")
    return True


def _api_reachable(base: str) -> bool:
    try:
        urllib.request.urlopen(f"{base.rstrip('/')}/health/", timeout=3)
        return True
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Elite Fintech self-check suite")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Also run live HTTP smoke test (requires API on SMOKE_BASE_URL)",
    )
    parser.add_argument(
        "--skip-migrate",
        action="store_true",
        help="Skip migrate step (CI may run migrate separately)",
    )
    args = parser.parse_args()

    python = sys.executable
    smoke_base = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000")
    failed: list[str] = []

    print("=" * 60)
    print("Elite Fintech Systems — SELF CHECK")
    print("=" * 60)

    steps: list[tuple[list[str], str]] = []

    if not args.skip_migrate:
        steps.append(([python, "manage.py", "migrate", "--noinput"], "Database migrations"))

    steps.extend(
        [
            ([python, "manage.py", "check"], "Django system check"),
            (
                [python, "manage.py", "makemigrations", "--check", "--dry-run"],
                "No pending model migrations",
            ),
            (
                [python, "manage.py", "test", "--verbosity", "1"],
                "Backend tests + API contract self-checks",
            ),
        ]
    )

    for cmd, label in steps:
        if not _run(cmd, label):
            failed.append(label)

    run_live = args.live or os.getenv("SELF_CHECK_LIVE", "").lower() in ("1", "true", "yes")
    if run_live:
        if _api_reachable(smoke_base):
            if not _run([python, "manage.py", "seed_demo"], "Seed demo MoMo data"):
                failed.append("Seed demo MoMo data")
            elif not _run([python, str(SCRIPTS_DIR / "smoke_live.py")], f"Live API smoke ({smoke_base})"):
                failed.append(f"Live API smoke ({smoke_base})")
        else:
            print(f"\n--- Live API smoke ({smoke_base}) ---")
            print(f"[SKIP] API not reachable at {smoke_base}")
            print("       Start with: npm run dev:backend")
            print("       Then run:   npm run check:live")

    print("\n" + "=" * 60)
    if failed:
        print(f"SELF CHECK FAILED — {len(failed)} step(s):")
        for name in failed:
            print(f"  • {name}")
        print("=" * 60)
        return 1

    print("SELF CHECK PASSED — safe to continue")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
