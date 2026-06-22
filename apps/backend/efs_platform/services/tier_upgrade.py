"""PLATINUM tier upgrade via Setup Transfer automation."""

from __future__ import annotations

from django.utils import timezone

from config.readiness import readiness_summary
from efs_platform.services.tier import TIER_MATRIX, get_platform_profile


def platinum_readiness_eligible() -> tuple[bool, int, list[dict]]:
    summary = readiness_summary()
    score = summary["score"]
    # Allow automation to proceed at 80+ with warnings; 95+ is fully eligible
    eligible = score >= 80
    return eligible, score, summary["gaps"]


def build_platinum_upgrade_manifest(org, transfer, request) -> dict:
    from efs_platform.services.provisioning import build_setup_manifest

    base_manifest = build_setup_manifest(org, transfer, request)
    eligible, score, gaps = platinum_readiness_eligible()
    profile = get_platform_profile()
    next_caps = TIER_MATRIX["PLATINUM"]

    production_api = request.build_absolute_uri("/").rstrip("/")
    production_web = "https://elite-fintech-web-production.up.railway.app"

    env = dict(base_manifest.get("environment", {}))
    env.update(
        {
            "PLATFORM_TIER": "PLATINUM",
            "CLIENT_URL": production_web,
            "DEBUG": "False",
        }
    )

    upgrade_steps = [
        {"id": "readiness_check", "label": f"Readiness score {score}/100", "done": score >= 80},
        {"id": "tier_upgrade", "label": "Apply PLATFORM_TIER=PLATINUM", "done": "tier_upgrade" in transfer.completed_steps},
        {"id": "redis_realtime", "label": "Attach REDIS_URL for multi-instance WebSockets", "done": bool(env.get("REDIS_URL"))},
        {"id": "backup_schedule", "label": "Schedule scripts/backup-db.sh nightly", "done": "backup_schedule" in transfer.completed_steps},
        {"id": "client_url", "label": "Set CLIENT_URL to production frontend", "done": True},
        {"id": "verify_capabilities", "label": "Verify /platform/capabilities/ shows PLATINUM", "done": "verify_capabilities" in transfer.completed_steps},
    ]

    transfer.metadata = {
        **(transfer.metadata or {}),
        "requested_tier": "PLATINUM",
        "readiness_score": score,
        "readiness_eligible": eligible,
        "upgrade_applied_at": timezone.now().isoformat(),
        "automation_agent": transfer.automation_agent or "cursor",
    }

    base_manifest.update(
        {
            "platform_tier": "PLATINUM" if "tier_upgrade" in transfer.completed_steps else profile["tier"],
            "target_tier": "PLATINUM",
            "readiness": {
                "score": score,
                "eligible": eligible,
                "gaps": gaps[:5],
                "deployment_tier": readiness_summary()["deployment_tier"],
            },
            "environment": env,
            "tier_upgrade": {
                "from_tier": profile["tier"],
                "to_tier": "PLATINUM",
                "capabilities_unlocked": [
                    c for c in next_caps if c["included"] and c["id"] not in {x["id"] for x in profile["capabilities"] if x["included"]}
                ],
            },
            "setup_steps": upgrade_steps + base_manifest.get("setup_steps", []),
            "deploy_actions": {
                "railway": {
                    "service": "elite-fintech-api",
                    "variables": {
                        "PLATFORM_TIER": "PLATINUM",
                        "CLIENT_URL": production_web,
                        "DEBUG": "False",
                    },
                    "note": "Set variables in Railway dashboard or: railway variables set PLATFORM_TIER=PLATINUM",
                },
                "verify": {
                    "health": f"{production_api}/health/",
                    "capabilities": f"{production_api}/api/v1/platform/capabilities/",
                    "readiness": f"{production_api}/api/v1/platform/readiness/",
                },
            },
            "message": (
                f"PLATINUM upgrade manifest ready (readiness {score}/100). "
                "Apply deploy_actions.railway.variables, redeploy API, then mark verify_capabilities complete."
            ),
        }
    )

    base_manifest["automation"] = {
        **base_manifest.get("automation", {}),
        "compatible_agents": ["cursor", "github_actions", "terraform", "custom"],
        "instructions": (
            "POST this manifest's deploy_actions to your host. "
            "For Railway: set PLATFORM_TIER=PLATINUM and CLIENT_URL, redeploy, then GET /platform/capabilities/."
        ),
        "tier_upgrade_endpoint": request.build_absolute_uri("/api/v1/platform/setup/apply/"),
    }

    return base_manifest


def apply_platinum_upgrade(transfer, completed_steps: list[str] | None = None) -> None:
    steps = list(transfer.completed_steps or [])
    if completed_steps:
        steps = list(set(steps + completed_steps))
    if "tier_upgrade" not in steps:
        steps.append("tier_upgrade")
    transfer.completed_steps = steps
    transfer.metadata = {
        **(transfer.metadata or {}),
        "requested_tier": "PLATINUM",
        "tier_upgrade_status": "applied",
    }
