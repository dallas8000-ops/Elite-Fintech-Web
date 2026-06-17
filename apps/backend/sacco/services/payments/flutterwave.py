from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import urllib.error
import urllib.request

from sacco.services.payments.base import ChargeResult

logger = logging.getLogger(__name__)

FLUTTERWAVE_API = "https://api.flutterwave.com/v3"


def is_flutterwave_configured() -> bool:
    return bool(os.getenv("FLUTTERWAVE_SECRET_KEY"))


def flutterwave_env() -> str:
    return os.getenv("FLUTTERWAVE_ENV", "sandbox").lower()


def _secret_key() -> str:
    key = os.getenv("FLUTTERWAVE_SECRET_KEY", "")
    if not key:
        raise RuntimeError("FLUTTERWAVE_SECRET_KEY not configured")
    return key


def _webhook_secret() -> str:
    return os.getenv("FLUTTERWAVE_WEBHOOK_SECRET", _secret_key())


def verify_webhook_signature(body: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    expected = hmac.new(_webhook_secret().encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _request(method: str, path: str, payload: dict | None = None) -> dict:
    url = f"{FLUTTERWAVE_API}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {_secret_key()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        logger.warning("Flutterwave HTTP %s: %s", exc.code, detail)
        try:
            return json.loads(detail)
        except json.JSONDecodeError:
            return {"status": "error", "message": detail}


def normalize_uganda_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("256"):
        return digits
    if digits.startswith("0"):
        return "256" + digits[1:]
    if len(digits) == 9:
        return "256" + digits
    return digits


def flutterwave_network(momo_network: str) -> str:
    if momo_network == "AIRTEL":
        return "AIRTEL"
    return "MTN"


class FlutterwaveAdapter:
    def initiate_mobile_money(
        self,
        *,
        phone: str,
        amount_minor: int,
        currency: str,
        email: str,
        tx_ref: str,
        network: str,
        meta: dict,
    ) -> ChargeResult:
        phone_number = normalize_uganda_phone(phone)
        body = {
            "phone_number": phone_number,
            "amount": amount_minor,
            "currency": currency.upper(),
            "email": email,
            "tx_ref": tx_ref,
            "network": flutterwave_network(network),
            "meta": meta,
        }
        result = _request("POST", "/charges?type=mobile_money_uganda", body)
        data = result.get("data") or {}
        status = (data.get("status") or result.get("status") or "pending").lower()
        message = data.get("processor_response") or result.get("message") or "MoMo prompt sent"
        return ChargeResult(
            provider_reference=tx_ref,
            status=status,
            message=message,
            payment_url=data.get("link"),
            provider_transaction_id=str(data.get("id")) if data.get("id") else None,
            raw=result,
        )

    def verify_transaction(self, transaction_id: str) -> dict:
        return _request("GET", f"/transactions/{transaction_id}/verify")


def get_flutterwave_adapter() -> FlutterwaveAdapter:
    return FlutterwaveAdapter()
