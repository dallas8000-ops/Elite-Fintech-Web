from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request

from sacco.services.payments.base import ChargeResult

logger = logging.getLogger(__name__)

FLUTTERWAVE_API_V3 = "https://api.flutterwave.com/v3"
FLUTTERWAVE_API_V4_SANDBOX = "https://developersandbox-api.flutterwave.com"
FLUTTERWAVE_API_V4_LIVE = "https://api.flutterwave.com"
FLUTTERWAVE_TOKEN_URL = (
    "https://idp.flutterwave.com/realms/flutterwave/protocol/openid-connect/token"
)
_token_cache: dict[str, float | str] = {"access_token": "", "expires_at": 0.0}


def is_flutterwave_configured() -> bool:
    if os.getenv("FLUTTERWAVE_SECRET_KEY", "").strip():
        return True
    return bool(
        os.getenv("FLUTTERWAVE_CLIENT_ID", "").strip()
        and os.getenv("FLUTTERWAVE_CLIENT_SECRET", "").strip()
    )


def flutterwave_env() -> str:
    return os.getenv("FLUTTERWAVE_ENV", "sandbox").lower()


def _secret_key() -> str:
    key = os.getenv("FLUTTERWAVE_SECRET_KEY", "").strip()
    if key:
        return key
    client_secret = os.getenv("FLUTTERWAVE_CLIENT_SECRET", "").strip()
    if client_secret:
        return client_secret
    raise RuntimeError("Flutterwave credentials not configured")


def _bearer_token() -> str:
    static = os.getenv("FLUTTERWAVE_SECRET_KEY", "").strip()
    if static.startswith("FLWSECK"):
        return static

    client_id = os.getenv("FLUTTERWAVE_CLIENT_ID", "").strip()
    client_secret = os.getenv("FLUTTERWAVE_CLIENT_SECRET", "").strip()
    if client_id and client_secret:
        now = time.time()
        cached = str(_token_cache.get("access_token", ""))
        expires_at = float(_token_cache.get("expires_at", 0.0))
        if cached and expires_at > now + 30:
            return cached

        body = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            }
        ).encode()
        req = urllib.request.Request(
            FLUTTERWAVE_TOKEN_URL,
            data=body,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode()
            logger.warning("Flutterwave OAuth HTTP %s: %s", exc.code, detail)
            raise RuntimeError("Flutterwave OAuth token request failed") from exc

        token = payload.get("access_token")
        if not token:
            raise RuntimeError(payload.get("error_description") or "Flutterwave OAuth token missing")
        _token_cache["access_token"] = token
        _token_cache["expires_at"] = now + int(payload.get("expires_in", 300))
        return token

    if static:
        return static
    raise RuntimeError("Flutterwave credentials not configured")


def _uses_v4_oauth() -> bool:
    static = os.getenv("FLUTTERWAVE_SECRET_KEY", "").strip()
    if static.startswith("FLWSECK"):
        return False
    return bool(
        os.getenv("FLUTTERWAVE_CLIENT_ID", "").strip()
        and os.getenv("FLUTTERWAVE_CLIENT_SECRET", "").strip()
    )


def _api_base() -> str:
    if _uses_v4_oauth():
        if flutterwave_env() == "sandbox":
            return os.getenv("FLUTTERWAVE_V4_API", FLUTTERWAVE_API_V4_SANDBOX).rstrip("/")
        return os.getenv("FLUTTERWAVE_V4_API", FLUTTERWAVE_API_V4_LIVE).rstrip("/")
    return FLUTTERWAVE_API_V3


def _request_headers(scenario_key: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {_bearer_token()}",
        "Content-Type": "application/json",
    }
    if _uses_v4_oauth():
        headers["X-Trace-Id"] = str(uuid.uuid4())
        headers["X-Idempotency-Key"] = str(uuid.uuid4())
        if scenario_key:
            headers["X-Scenario-Key"] = scenario_key
    return headers


def _webhook_secret() -> str:
    explicit = os.getenv("FLUTTERWAVE_WEBHOOK_SECRET", "").strip()
    if explicit:
        return explicit
    static = os.getenv("FLUTTERWAVE_SECRET_KEY", "").strip()
    if static.startswith("FLWSECK"):
        return static
    return ""


def verify_webhook_signature(body: bytes, signature: str | None) -> bool:
    """Flutterwave sends your dashboard secret hash in the verif-hash header (plain compare)."""
    secret = _webhook_secret()
    if not secret or not signature:
        return False
    return hmac.compare_digest(signature.strip(), secret.strip())


def _request(method: str, path: str, payload: dict | None = None, *, scenario_key: str | None = None) -> dict:
    url = f"{_api_base()}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers=_request_headers(scenario_key),
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


SANDBOX_DEMO_PUBLIC_KEY = "FLWPUBK_TEST-SANDBOXDEMOKEY-X"


def hosted_pay_public_key() -> str:
    explicit = os.getenv("FLUTTERWAVE_PUBLIC_KEY", "").strip()
    if explicit:
        return explicit
    if flutterwave_env() == "sandbox":
        return SANDBOX_DEMO_PUBLIC_KEY
    return ""


def payment_options_for_checkout(rail: str, country: str) -> str:
    code = (country or "UG").upper()
    momo_by_country = {
        "UG": "mobilemoneyuganda",
        "KE": "mobilemoneykenya",
        "TZ": "mobilemoneytanzania",
        "RW": "mobilemoneyrwanda",
    }
    momo = momo_by_country.get(code, "mobilemoneyuganda")
    if rail == "MOBILE_MONEY":
        return momo
    if rail == "USSD":
        return "ussd"
    if rail == "CARD":
        return "card"
    return ",".join(dict.fromkeys([momo, "ussd", "card"]))


def _split_customer_name(name: str) -> dict[str, str]:
    parts = [p for p in name.split() if p]
    if not parts:
        return {"first": "Customer", "last": "User"}
    if len(parts) == 1:
        return {"first": parts[0], "last": "User"}
    if len(parts) == 2:
        return {"first": parts[0], "last": parts[1]}
    return {"first": parts[0], "middle": parts[1], "last": " ".join(parts[2:])}


def _uganda_momo_parts(phone: str) -> tuple[str, str]:
    digits = normalize_uganda_phone(phone)
    if digits.startswith("256") and len(digits) > 3:
        return "256", digits[3:]
    return "256", digits[-9:] if len(digits) >= 9 else digits


def _create_v4_customer(email: str, customer_name: str) -> str:
    result = _request(
        "POST",
        "/customers",
        {
            "email": email,
            "name": _split_customer_name(customer_name),
        },
    )
    data = result.get("data") or {}
    customer_id = data.get("id")
    if customer_id:
        return customer_id

    error = result.get("error") or {}
    message = (error.get("message") or result.get("message") or "").lower()
    if "already exists" in message:
        listing = _request("GET", "/customers?page=1&size=50")
        for customer in listing.get("data") or []:
            if customer.get("email") == email and customer.get("id"):
                return customer["id"]

    raise RuntimeError(result.get("message") or error.get("message") or "Flutterwave customer creation failed")


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
        if _uses_v4_oauth():
            return self._initiate_mobile_money_v4(
                phone=phone,
                amount_minor=amount_minor,
                currency=currency,
                email=email,
                tx_ref=tx_ref,
                network=network,
                meta=meta,
            )

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

    def _initiate_mobile_money_v4(
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
        country_code, phone_number = _uganda_momo_parts(phone)
        result = _request(
            "POST",
            "/orchestration/direct-charges",
            {
                "amount": amount_minor,
                "currency": currency.upper(),
                "reference": tx_ref,
                "customer": {
                    "email": email,
                    "name": _split_customer_name(meta.get("member_name", "SACCO Member")),
                },
                "payment_method": {
                    "type": "mobile_money",
                    "mobile_money": {
                        "network": flutterwave_network(network),
                        "country_code": country_code,
                        "phone_number": phone_number,
                    },
                },
                "meta": meta,
            },
        )
        data = result.get("data") or {}
        next_action = data.get("next_action") or {}
        redirect = next_action.get("redirect_url") or {}
        payment_url = redirect.get("url") if isinstance(redirect, dict) else redirect
        instruction = next_action.get("payment_instruction") or {}
        message = (
            instruction.get("note")
            or data.get("processor_response", {}).get("type")
            or result.get("message")
            or "MoMo prompt sent"
        )
        status = (data.get("status") or result.get("status") or "pending").lower()
        return ChargeResult(
            provider_reference=tx_ref,
            status=status,
            message=message,
            payment_url=payment_url,
            provider_transaction_id=str(data.get("id")) if data.get("id") else None,
            raw=result,
        )

    def verify_transaction(self, transaction_id: str) -> dict:
        if _uses_v4_oauth():
            return _request("GET", f"/charges/{transaction_id}")
        return _request("GET", f"/transactions/{transaction_id}/verify")

    def authorize_charge_otp(self, charge_id: str, otp_code: str) -> dict:
        return _request(
            "PUT",
            f"/charges/{charge_id}",
            {
                "authorization": {
                    "type": "otp",
                    "otp": {"code": otp_code},
                }
            },
        )

    def create_hosted_checkout(
        self,
        *,
        tx_ref: str,
        amount: int,
        currency: str,
        email: str,
        customer_name: str,
        title: str,
        description: str,
        redirect_url: str,
        rail: str,
        country: str,
        meta: dict,
    ) -> dict:
        if _uses_v4_oauth():
            customer_id = _create_v4_customer(email, customer_name)
            result = _request(
                "POST",
                "/checkout/sessions",
                {
                    "amount": amount,
                    "currency": currency.upper(),
                    "customer_id": customer_id,
                    "reference": tx_ref,
                    "redirect_url": redirect_url,
                    "session_duration": 60,
                },
            )
            data = result.get("data") or {}
            if (result.get("status") or "").lower() == "failed" and not data.get("id"):
                error = result.get("error") or {}
                message = error.get("message") or result.get("message") or "Flutterwave checkout failed"
                raise RuntimeError(message)
            checkout_url = data.get("checkout_url")
            if not checkout_url and data.get("id"):
                fetched = _request("GET", f"/checkout/sessions/{data['id']}")
                checkout_url = (fetched.get("data") or {}).get("checkout_url")
            if not checkout_url and data.get("id"):
                from billing.flutterwave_hosted import build_hosted_pay_url

                checkout_url = build_hosted_pay_url(
                    data["id"],
                    rail=rail,
                    country=country,
                    organization_id=str(meta.get("organization_id") or ""),
                    tier=str(meta.get("tier") or ""),
                )
            return {
                "link": checkout_url,
                "status": result.get("status"),
                "message": result.get("message"),
                "env": flutterwave_env(),
                "raw": result,
            }

        body = {
            "tx_ref": tx_ref,
            "amount": amount,
            "currency": currency.upper(),
            "redirect_url": redirect_url,
            "customer": {"email": email, "name": customer_name},
            "customizations": {"title": title, "description": description},
            "meta": meta,
            "payment_options": payment_options_for_checkout(rail, country),
        }
        result = _request("POST", "/payments", body)
        data = result.get("data") or {}
        return {
            "link": data.get("link"),
            "status": result.get("status"),
            "message": result.get("message"),
            "env": flutterwave_env(),
            "raw": result,
        }


def get_flutterwave_adapter() -> FlutterwaveAdapter:
    return FlutterwaveAdapter()
