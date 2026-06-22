"""Production readiness scoring — used by /health/ and /api/v1/platform/readiness/."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict

from django.conf import settings
from django.db import connection


class ReadinessCheck(TypedDict):
    id: str
    label: str
    passed: bool
    weight: int
    fix: str | None


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKUP_SCRIPT = REPO_ROOT / "scripts" / "backup-db.sh"
_LOCAL_CLIENT_URL = "http://localhost:5173"


def _check(
    check_id: str,
    label: str,
    weight: int,
    passed: bool,
    fix_when_fail: str | None = None,
) -> ReadinessCheck:
    return {
        "id": check_id,
        "label": label,
        "passed": passed,
        "weight": weight,
        "fix": None if passed else fix_when_fail,
    }


def _database_ok() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except Exception:
        return False


def _database_url_ok() -> bool:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        return False
    return url.startswith(("postgresql://", "postgres://"))


def _stripe_ok() -> bool:
    return bool(os.getenv("STRIPE_SECRET_KEY", "").startswith("sk_"))


def _secret_key_ok() -> bool:
    key = os.getenv("SECRET_KEY", "")
    return key not in ("", "dev-insecure-change-in-production")


def _redis_ok() -> bool:
    return bool(os.getenv("REDIS_URL", ""))


def _deploy_platform_ok() -> bool:
    markers = (
        "RAILWAY_ENVIRONMENT",
        "RAILWAY_PUBLIC_DOMAIN",
        "RENDER",
        "FLY_APP_NAME",
        "DOCKER",
    )
    return any(os.getenv(m) for m in markers) or (REPO_ROOT / "docker-compose.yml").exists()


def _client_url_ok() -> bool:
    client_url = settings.CLIENT_URL or ""
    return bool(client_url and client_url != _LOCAL_CLIENT_URL)


def _prod_check(
    is_prod: bool,
    check_id: str,
    label: str,
    weight: int,
    passed: bool,
    fix_when_fail: str,
) -> ReadinessCheck:
    return _check(check_id, label, weight, passed if is_prod else True, fix_when_fail)


def run_readiness_checks() -> list[ReadinessCheck]:
    is_prod = not settings.DEBUG
    db_ok = _database_ok()
    backup_ok = BACKUP_SCRIPT.is_file()
    debug_ok = not settings.DEBUG
    secret_ok = _secret_key_ok()
    db_url_ok = _database_url_ok()
    redis_ok = _redis_ok()
    client_ok = _client_url_ok()

    return [
        _check("database", "Database connectivity", 14, db_ok, "Verify DATABASE_URL and run migrations"),
        _prod_check(
            is_prod,
            "database_url",
            "PostgreSQL DATABASE_URL",
            12,
            db_url_ok,
            "Store DATABASE_URL in vault (postgresql://...)",
        ),
        _check(
            "backup_script",
            "Database backup script",
            12,
            backup_ok,
            "Add scripts/backup-db.sh and schedule nightly runs",
        ),
        _check("health_endpoint", "Health check endpoint", 10, True, None),
        _prod_check(
            is_prod,
            "debug_disabled",
            "DEBUG disabled in production",
            12,
            debug_ok,
            "Set DEBUG=False in production",
        ),
        _prod_check(
            is_prod,
            "secret_key",
            "Strong SECRET_KEY",
            10,
            secret_ok,
            "Generate a strong SECRET_KEY",
        ),
        _check(
            "stripe",
            "Stripe billing configured",
            10,
            _stripe_ok(),
            "Configure STRIPE_SECRET_KEY and webhook secret",
        ),
        _prod_check(
            is_prod,
            "redis",
            "Redis for realtime layer",
            8,
            redis_ok,
            "Set REDIS_URL for multi-instance WebSockets",
        ),
        _check("deploy_platform", "Deployment platform detected", 6, _deploy_platform_ok(), None),
        _prod_check(
            is_prod,
            "client_url",
            "CLIENT_URL configured",
            6,
            client_ok,
            "Set CLIENT_URL to your live frontend URL",
        ),
    ]


def readiness_score(checks: list[ReadinessCheck] | None = None) -> int:
    checks = checks or run_readiness_checks()
    total_weight = sum(c["weight"] for c in checks)
    earned = sum(c["weight"] for c in checks if c["passed"])
    if total_weight == 0:
        return 0
    return round(earned / total_weight * 100)


def deployment_tier_for_score(score: int) -> str:
    if score >= 95:
        return "PLATINUM"
    if score >= 80:
        return "ENTERPRISE"
    if score >= 60:
        return "PRO"
    return "BASIC"


def readiness_summary() -> dict:
    checks = run_readiness_checks()
    score = readiness_score(checks)
    failed = [c for c in checks if not c["passed"]]
    tier = deployment_tier_for_score(score)
    return {
        "score": score,
        "deployment_tier": tier,
        "checks": checks,
        "passed": len(checks) - len(failed),
        "total": len(checks),
        "gaps": [{"id": c["id"], "label": c["label"], "fix": c["fix"]} for c in failed if c["fix"]],
    }
