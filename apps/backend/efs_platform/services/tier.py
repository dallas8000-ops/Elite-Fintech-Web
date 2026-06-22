"""Platform tier — ENTERPRISE default with PLATINUM institutional upgrade path."""

from __future__ import annotations

import os
from typing import TypedDict


class TierCapability(TypedDict):
    id: str
    label: str
    included: bool
    note: str


PLATFORM_TIER = os.getenv("PLATFORM_TIER", "ENTERPRISE").upper()
PLATFORM_NAME = "Elite Fintech Systems"
PLATFORM_TAGLINE = "Enterprise billing infrastructure for East African fintech"
PLATINUM_TAGLINE = "Institutional-grade billing for banks, telcos, and licensed PSPs"

TIER_ORDER = ("BASIC", "PRO", "ENTERPRISE", "PLATINUM")

TIER_MATRIX: dict[str, list[TierCapability]] = {
    "BASIC": [
        {"id": "single_tenant", "label": "Single tenant", "included": True, "note": ""},
        {"id": "card_only", "label": "Card payments only", "included": True, "note": "Stripe-style"},
        {"id": "custom_domain", "label": "Custom domain", "included": False, "note": ""},
        {"id": "african_rails", "label": "Mobile money rails", "included": False, "note": ""},
        {"id": "automation_api", "label": "AI provisioning API", "included": False, "note": ""},
    ],
    "PRO": [
        {"id": "multi_tenant", "label": "Multi-tenant orgs", "included": True, "note": ""},
        {"id": "local_billing", "label": "UGX / KES / RWF / TZS billing", "included": True, "note": ""},
        {"id": "momo", "label": "MoMo + USSD", "included": True, "note": "Flutterwave/Pesapal"},
        {"id": "custom_domain", "label": "Custom domain", "included": False, "note": ""},
        {"id": "automation_api", "label": "Setup transfer API", "included": False, "note": ""},
    ],
    "ENTERPRISE": [
        {"id": "multi_tenant", "label": "Multi-tenant isolation", "included": True, "note": "Org-scoped JWT"},
        {"id": "african_rails", "label": "Rail-first East Africa payments", "included": True, "note": "MoMo, USSD, agents"},
        {"id": "custom_domain", "label": "Custom domain white-label", "included": True, "note": "api + app subdomains"},
        {"id": "compliance", "label": "Data protection + local VAT", "included": True, "note": "UG/KE/RW/TZ"},
        {"id": "realtime", "label": "Django Channels live ops", "included": True, "note": ""},
        {"id": "rbac", "label": "Enterprise RBAC", "included": True, "note": ""},
        {"id": "automation_api", "label": "AI automation setup transfer", "included": True, "note": "Cursor / CI / agents"},
        {"id": "webhook_mesh", "label": "Multi-PSP webhook mesh", "included": True, "note": ""},
        {"id": "settlement_ops", "label": "Wallet settlement tracking", "included": True, "note": ""},
    ],
    "PLATINUM": [
        {"id": "multi_tenant", "label": "Multi-tenant isolation", "included": True, "note": "Org-scoped JWT"},
        {"id": "african_rails", "label": "Rail-first East Africa payments", "included": True, "note": "MoMo, USSD, agents"},
        {"id": "custom_domain", "label": "Custom domain white-label", "included": True, "note": "api + app subdomains"},
        {"id": "compliance", "label": "Data protection + local VAT", "included": True, "note": "UG/KE/RW/TZ"},
        {"id": "realtime", "label": "Django Channels live ops", "included": True, "note": "Redis-backed multi-instance"},
        {"id": "rbac", "label": "Enterprise RBAC", "included": True, "note": ""},
        {"id": "automation_api", "label": "AI automation setup transfer", "included": True, "note": "Cursor / CI / agents"},
        {"id": "webhook_mesh", "label": "Multi-PSP webhook mesh", "included": True, "note": "mTLS + signed payloads"},
        {"id": "settlement_ops", "label": "Wallet settlement tracking", "included": True, "note": ""},
        {"id": "dedicated_tenancy", "label": "Dedicated tenancy / isolated DB", "included": True, "note": "Per-org schema or VPC"},
        {"id": "dr_failover", "label": "Multi-region DR failover", "included": True, "note": "Active-passive replica"},
        {"id": "audit_export", "label": "Immutable audit log export", "included": True, "note": "WORM / SIEM feed"},
        {"id": "regulatory_reporting", "label": "Central bank reporting hooks", "included": True, "note": "BoU, CBK, BNR, BoT"},
        {"id": "sla_monitoring", "label": "99.9% SLA monitoring", "included": True, "note": "PagerDuty / Opsgenie"},
    ],
}

TIER_UPGRADE_HINTS: dict[str, list[str]] = {
    "ENTERPRISE": [
        "Schedule nightly pg_dump backups (scripts/backup-db.sh)",
        "Attach Redis for multi-instance WebSocket fan-out",
        "Set CLIENT_URL to your production frontend domain",
        "Enable PLATINUM with PLATFORM_TIER=PLATINUM after readiness ≥ 95",
    ],
    "PLATINUM": [
        "Provision dedicated Postgres per tenant group",
        "Configure cross-region read replica + failover runbook",
        "Wire audit export to your SIEM (Splunk / Datadog)",
        "Register central bank regulatory webhook endpoints",
    ],
}


def _active_tier() -> str:
    tier = PLATFORM_TIER if PLATFORM_TIER in TIER_MATRIX else "ENTERPRISE"
    return tier


def _next_tier(tier: str) -> str | None:
    try:
        idx = TIER_ORDER.index(tier)
    except ValueError:
        return None
    if idx + 1 < len(TIER_ORDER):
        return TIER_ORDER[idx + 1]
    return None


def get_platform_profile() -> dict:
    tier = _active_tier()
    next_tier = _next_tier(tier)
    profile = {
        "tier": tier,
        "name": PLATFORM_NAME,
        "tagline": PLATINUM_TAGLINE if tier == "PLATINUM" else PLATFORM_TAGLINE,
        "region": "East Africa — Uganda, Kenya, Rwanda, Tanzania",
        "capabilities": TIER_MATRIX[tier],
        "comparison": {t: sum(1 for c in caps if c["included"]) for t, caps in TIER_MATRIX.items()},
        "tier_ladder": list(TIER_ORDER),
    }
    if next_tier:
        profile["next_tier"] = next_tier
        profile["upgrade_capabilities"] = [
            c for c in TIER_MATRIX[next_tier] if c["included"] and c["id"] not in {x["id"] for x in TIER_MATRIX[tier] if x["included"]}
        ]
        profile["upgrade_hints"] = TIER_UPGRADE_HINTS.get(tier, [])
    return profile
