"""Confirm Flutterwave v4 charges and activate subscriptions without waiting on webhooks."""

from __future__ import annotations

import logging
import os

from billing.services.flutterwave_checkout import BILLING_TX_REF_PREFIX, handle_subscription_webhook
from sacco.services.payments.flutterwave import flutterwave_env, get_flutterwave_adapter

logger = logging.getLogger(__name__)

_SUCCESS_STATUSES = frozenset({"successful", "success", "succeeded"})
_PENDING_STATUSES = frozenset({"pending", "processing", "in_progress"})
_OTP_ACTIONS = frozenset({"requires_otp", "otp", "payment_instruction"})


def _charge_data(charge_id: str) -> dict:
    adapter = get_flutterwave_adapter()
    result = adapter.verify_transaction(charge_id)
    return result.get("data") or result


def _next_action_type(data: dict) -> str:
    next_action = data.get("next_action") or {}
    return str(next_action.get("type") or "").lower()


def authorize_billing_charge_otp(charge_id: str, otp_code: str) -> dict:
    adapter = get_flutterwave_adapter()
    result = adapter.authorize_charge_otp(charge_id, otp_code)
    data = result.get("data") or result
    status = (data.get("status") or result.get("status") or "").lower()
    return {"status": status, "data": data, "raw": result}


def try_activate_billing_charge(
    *,
    charge_id: str | None,
    tx_ref: str,
    org_id: str,
    tier: str,
    rail: str,
    amount: int | None = None,
    otp_code: str | None = None,
) -> dict:
    """Poll Flutterwave for charge status and activate subscription when paid."""
    if not tx_ref.startswith(BILLING_TX_REF_PREFIX):
        return {"activated": False, "status": "invalid_reference", "error": "Not a billing checkout"}

    if not charge_id:
        return {"activated": False, "status": "missing_charge_id", "error": "Charge ID required"}

    data = _charge_data(charge_id)
    status = (data.get("status") or "").lower()
    action_type = _next_action_type(data)

    if otp_code and (status in _PENDING_STATUSES or action_type in _OTP_ACTIONS):
        authorize_billing_charge_otp(charge_id, otp_code)
        data = _charge_data(charge_id)
        status = (data.get("status") or "").lower()
        action_type = _next_action_type(data)

    if (
        status in _PENDING_STATUSES
        and action_type in _OTP_ACTIONS
        and flutterwave_env() == "sandbox"
        and not otp_code
    ):
        sandbox_otp = os.getenv("FLUTTERWAVE_SANDBOX_OTP", "123456")
        authorize_billing_charge_otp(charge_id, sandbox_otp)
        data = _charge_data(charge_id)
        status = (data.get("status") or "").lower()
        action_type = _next_action_type(data)

    if status not in _SUCCESS_STATUSES:
        return {
            "activated": False,
            "status": status or "pending",
            "next_action": action_type or _next_action_type(data),
            "requires_otp": action_type in _OTP_ACTIONS,
        }

    meta = data.get("meta") or {}
    if not meta.get("organization_id"):
        meta = {
            **meta,
            "organization_id": org_id,
            "tier": tier,
            "rail": rail,
            "checkout_type": "subscription",
        }

    webhook_data = {
        **data,
        "reference": data.get("reference") or tx_ref,
        "tx_ref": data.get("tx_ref") or data.get("reference") or tx_ref,
        "amount": data.get("amount") or amount,
        "meta": meta,
        "status": "successful",
    }
    handle_subscription_webhook(webhook_data, {"event": "charge.completed"})
    logger.info("Activated subscription from charge %s (%s)", charge_id, tx_ref)
    return {"activated": True, "status": "successful", "tx_ref": tx_ref}
