"""Platform tier — ENTERPRISE positioning for East Africa."""

from __future__ import annotations

from typing import TypedDict


class TierCapability(TypedDict):
    id: str
    label: str
    included: bool
    note: str


PLATFORM_TIER = "ENTERPRISE"
PLATFORM_NAME = "Elite Fintech Systems"
PLATFORM_TAGLINE = "Enterprise billing infrastructure for East African fintech"

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
}


def get_platform_profile() -> dict:
    return {
        "tier": PLATFORM_TIER,
        "name": PLATFORM_NAME,
        "tagline": PLATFORM_TAGLINE,
        "region": "East Africa — Uganda, Kenya, Rwanda, Tanzania",
        "capabilities": TIER_MATRIX[PLATFORM_TIER],
        "comparison": {
            tier: sum(1 for c in caps if c["included"])
            for tier, caps in TIER_MATRIX.items()
        },
    }
