"""Flutterwave checkout bridge for v4 sandbox (MoMo direct charge) and v3 hosted pay."""

from __future__ import annotations

import html
import json
import os
import urllib.parse

from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from billing.services.flutterwave_confirm import try_activate_billing_charge

from sacco.services.payments.flutterwave import (
    _request,
    _uses_v4_oauth,
    flutterwave_env,
    get_flutterwave_adapter,
    hosted_pay_public_key,
    payment_options_for_checkout,
)

HOSTED_PAY_ACTION = "https://checkout.flutterwave.com/v3/hosted/pay"


def _checkout_bridge_base() -> str:
    """Prefer the frontend origin so dev checkout stays on the Vite proxy."""
    client = os.getenv("CLIENT_URL", "").strip().rstrip("/")
    if client:
        return client
    public = os.getenv("DJANGO_PUBLIC_URL", "").strip().rstrip("/")
    if public:
        return public
    return "http://localhost:5175"


def build_hosted_pay_url(
    session_id: str,
    *,
    rail: str = "MOBILE_MONEY",
    country: str = "UG",
    organization_id: str | None = None,
    tier: str | None = None,
) -> str:
    params: dict[str, str] = {
        "session": session_id,
        "rail": rail,
        "country": country,
    }
    if organization_id:
        params["org"] = organization_id
    if tier:
        params["tier"] = tier
    return f"{_checkout_bridge_base()}/billing/flutterwave/pay/?{urllib.parse.urlencode(params)}"


def _session_context(session_id: str) -> tuple[dict, str | None]:
    fetched = _request("GET", f"/checkout/sessions/{session_id}")
    session = fetched.get("data") or {}
    if not session.get("id"):
        message = fetched.get("message") or "Checkout session not found"
        return {}, message

    customer_email = "checkout@elitefintech.co.ug"
    customer_name = "Elite Fintech Customer"
    customer_id = session.get("customer_id") or ""
    if customer_id:
        customer = (_request("GET", f"/customers/{customer_id}").get("data")) or {}
        customer_email = customer.get("email") or customer_email
        name = customer.get("name") or {}
        if isinstance(name, dict):
            parts = [name.get("first"), name.get("middle"), name.get("last")]
            customer_name = " ".join(p for p in parts if p) or customer_name

    session["customer_email"] = customer_email
    session["customer_name"] = customer_name
    return session, None


def _format_amount(amount: object, currency: str) -> str:
    try:
        value = int(amount)
    except (TypeError, ValueError):
        return f"{amount} {currency}"
    return f"{value:,} {currency.upper()}"


def _page(title: str, body: str) -> HttpResponse:
    content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; background: #0f1419; color: #e7ecf3; margin: 0; }}
    .wrap {{ max-width: 420px; margin: 48px auto; padding: 24px; }}
    .card {{ background: #171d25; border: 1px solid #2a3441; border-radius: 12px; padding: 24px; }}
    h1 {{ font-size: 1.25rem; margin: 0 0 8px; }}
    p {{ color: #9aa7b8; line-height: 1.5; }}
    label {{ display: block; font-size: 0.875rem; margin-bottom: 6px; color: #c5d0de; }}
    input, select {{ width: 100%; box-sizing: border-box; padding: 10px 12px; border-radius: 8px;
      border: 1px solid #2a3441; background: #0f1419; color: #e7ecf3; margin-bottom: 14px; }}
    button, .btn {{ display: inline-block; width: 100%; padding: 12px; border: 0; border-radius: 8px;
      background: #059669; color: white; font-weight: 600; cursor: pointer; text-decoration: none; text-align: center; }}
    .muted {{ font-size: 0.8rem; }}
    .error {{ color: #f87171; margin-bottom: 12px; }}
    .success {{ color: #34d399; }}
    .amount {{ font-size: 1.5rem; font-weight: 700; color: #34d399; margin: 12px 0 20px; }}
  </style>
</head>
<body>
  <div class="wrap"><div class="card">{body}</div></div>
</body>
</html>"""
    return HttpResponse(content, content_type="text/html; charset=utf-8")


@method_decorator(csrf_exempt, name="dispatch")
class FlutterwaveHostedPayView(View):
    """MoMo direct-charge bridge for v4 sandbox; v3 hosted pay for legacy keys."""

    def get(self, request):
        session_id = request.GET.get("session", "").strip()
        if not session_id:
            return HttpResponse("Missing checkout session", status=400)

        session, error = _session_context(session_id)
        if error:
            return HttpResponse(error, status=404)

        rail = request.GET.get("rail", "MOBILE_MONEY").upper()
        country = request.GET.get("country", "UG").upper()
        tier = request.GET.get("tier", "PRO")
        org_id = request.GET.get("org", "")
        amount = session.get("amount")
        currency = session.get("currency") or "UGX"
        redirect_url = session.get("redirect_url") or os.getenv("CLIENT_URL", "http://localhost:5175")

        if rail == "MOBILE_MONEY" and _uses_v4_oauth():
            body = f"""
  <h1>Pay with Mobile Money</h1>
  <p class="muted">Flutterwave v4 sandbox · {html.escape(country)} · {html.escape(tier)} plan</p>
  <div class="amount">{html.escape(_format_amount(amount, currency))}</div>
  <p>Enter the mobile number that will receive the MoMo payment prompt.</p>
  <p class="muted"><strong>Sandbox:</strong> use any Uganda number (e.g. 0700000000). When prompted for OTP, enter <strong>123456</strong>.</p>
  <form method="post">
    <input type="hidden" name="session" value="{html.escape(session_id)}" />
    <input type="hidden" name="rail" value="{html.escape(rail)}" />
    <input type="hidden" name="country" value="{html.escape(country)}" />
    <input type="hidden" name="tier" value="{html.escape(tier)}" />
    <input type="hidden" name="org" value="{html.escape(org_id)}" />
    <label for="phone">Mobile number</label>
    <input id="phone" name="phone" type="tel" placeholder="e.g. 0700000000 or 256700000000" required />
    <label for="network">Network</label>
    <select id="network" name="network">
      <option value="MTN">MTN</option>
      <option value="AIRTEL">Airtel</option>
    </select>
    <button type="submit">Send MoMo prompt</button>
  </form>
  <p class="muted" style="margin-top:16px">You will not be redirected to checkout.flutterwave.com — v4 sandbox uses direct mobile money charges.</p>
"""
            return _page("Mobile Money Checkout", body)

        public_key = hosted_pay_public_key()
        if not public_key:
            return _page(
                "Checkout unavailable",
                "<p>Flutterwave public key not configured. For v4 sandbox, use the Mobile Money rail.</p>",
            )

        tx_ref = session.get("reference") or session_id
        payment_options = payment_options_for_checkout(rail, country)
        fields = {
            "public_key": public_key,
            "tx_ref": tx_ref,
            "amount": str(amount),
            "currency": currency,
            "redirect_url": redirect_url,
            "payment_options": payment_options,
            "customer[email]": session.get("customer_email", "checkout@elitefintech.co.ug"),
            "customer[name]": session.get("customer_name", "Elite Fintech Customer"),
            "customizations[title]": "Elite Fintech Systems",
            "customizations[description]": "Subscription checkout",
        }
        inputs = "\n".join(
            f'<input type="hidden" name="{html.escape(name)}" value="{html.escape(str(value))}" />'
            for name, value in fields.items()
            if value is not None and str(value) != ""
        )
        body = f"""
  <p>Redirecting to Flutterwave {html.escape(flutterwave_env())} checkout…</p>
  <form id="fw-pay" method="POST" action="{HOSTED_PAY_ACTION}">
    {inputs}
    <noscript><button type="submit">Continue to payment</button></noscript>
  </form>
  <script>document.getElementById("fw-pay").submit();</script>
"""
        return _page("Redirecting to Flutterwave", body)

    def post(self, request):
        session_id = request.POST.get("session", "").strip()
        phone = request.POST.get("phone", "").strip()
        rail = request.POST.get("rail", "MOBILE_MONEY").upper()
        country = request.POST.get("country", "UG").upper()
        tier = request.POST.get("tier", "PRO")
        org_id = request.POST.get("org", "")
        network = request.POST.get("network", "MTN").upper()

        if not session_id or not phone:
            return HttpResponse("Missing session or phone number", status=400)

        session, error = _session_context(session_id)
        if error:
            return HttpResponse(error, status=404)

        tx_ref = session.get("reference") or session_id
        amount = int(session.get("amount") or 0)
        currency = (session.get("currency") or "UGX").upper()
        redirect_url = session.get("redirect_url") or os.getenv("CLIENT_URL", "http://localhost:5175")
        email = session.get("customer_email", "checkout@elitefintech.co.ug")

        meta = {
            "organization_id": org_id,
            "tier": tier,
            "rail": rail,
            "checkout_type": "subscription",
            "flutterwave_session_id": session_id,
        }

        try:
            result = get_flutterwave_adapter().initiate_mobile_money(
                phone=phone,
                amount_minor=amount,
                currency=currency,
                email=email,
                tx_ref=tx_ref,
                network=network,
                meta=meta,
            )
        except Exception as exc:
            body = f'<p class="error">{html.escape(str(exc))}</p><p><a class="btn" href="javascript:history.back()">Try again</a></p>'
            return _page("Payment failed", body)

        instruction = result.message or "Check your phone to approve the MoMo payment."
        charge_id = result.provider_transaction_id or ""
        status_url = (
            f"/billing/flutterwave/pay/status/?charge={urllib.parse.quote(charge_id)}"
            f"&tx_ref={urllib.parse.quote(tx_ref)}"
            f"&org={urllib.parse.quote(org_id)}"
            f"&tier={urllib.parse.quote(tier)}"
            f"&rail={urllib.parse.quote(rail)}"
            f"&amount={amount}"
        )

        confirm = try_activate_billing_charge(
            charge_id=charge_id,
            tx_ref=tx_ref,
            org_id=org_id,
            tier=tier,
            rail=rail,
            amount=amount,
        )
        if confirm.get("activated"):
            body = f"""
  <h1>Payment confirmed</h1>
  <p class="success">Your {html.escape(tier)} subscription is now active.</p>
  <p class="muted">Reference: {html.escape(tx_ref)}</p>
  <p style="margin-top:20px"><a class="btn" href="{html.escape(redirect_url)}">Go to dashboard</a></p>
"""
            return _page("Payment confirmed", body)

        poll_js = json.dumps(status_url)
        redirect_js = json.dumps(redirect_url)
        body = f"""
  <h1>MoMo prompt sent</h1>
  <p class="success">{html.escape(instruction)}</p>
  <p class="muted">Amount: {html.escape(_format_amount(amount, currency))}</p>
  <p class="muted">Reference: {html.escape(tx_ref)}</p>
  <p id="status-line">Waiting for payment approval…</p>
  <form method="post" action="/billing/flutterwave/pay/otp/" style="margin-top:16px">
    <input type="hidden" name="charge" value="{html.escape(charge_id)}" />
    <input type="hidden" name="session" value="{html.escape(session_id)}" />
    <input type="hidden" name="tx_ref" value="{html.escape(tx_ref)}" />
    <input type="hidden" name="org" value="{html.escape(org_id)}" />
    <input type="hidden" name="tier" value="{html.escape(tier)}" />
    <input type="hidden" name="rail" value="{html.escape(rail)}" />
    <input type="hidden" name="amount" value="{amount}" />
    <input type="hidden" name="redirect_url" value="{html.escape(redirect_url)}" />
    <label for="otp">Sandbox OTP (if payment stays pending)</label>
    <input id="otp" name="otp" type="text" inputmode="numeric" value="123456" maxlength="8" />
    <button type="submit">Confirm with OTP</button>
  </form>
  <p class="muted">Sandbox default OTP: <strong>123456</strong>. Polling also tries this automatically.</p>
  <p style="margin-top:20px"><a class="btn" href="{html.escape(redirect_url)}">Return to dashboard</a></p>
  <script>
    (function () {{
      const statusUrl = {poll_js};
      const dashboardUrl = {redirect_js};
      let attempts = 0;
      const timer = setInterval(async () => {{
        attempts += 1;
        try {{
          const res = await fetch(statusUrl);
          const data = await res.json();
          if (data.activated) {{
            clearInterval(timer);
            document.getElementById("status-line").textContent = "Payment confirmed — subscription active.";
            window.location.href = dashboardUrl;
            return;
          }}
          if (attempts >= 40) {{
            clearInterval(timer);
            document.getElementById("status-line").textContent =
              "Still pending. Return to the dashboard after approving on your phone.";
          }}
        }} catch (e) {{
          if (attempts >= 40) clearInterval(timer);
        }}
      }}, 3000);
    }})();
  </script>
"""
        return _page("MoMo prompt sent", body)


@method_decorator(csrf_exempt, name="dispatch")
class FlutterwavePayOtpView(View):
    """Submit sandbox/production OTP to complete a pending MoMo charge."""

    def post(self, request):
        charge_id = request.POST.get("charge", "").strip()
        otp = request.POST.get("otp", "").strip()
        tx_ref = request.POST.get("tx_ref", "").strip()
        org_id = request.POST.get("org", "").strip()
        tier = request.POST.get("tier", "PRO").strip()
        rail = request.POST.get("rail", "MOBILE_MONEY").strip()
        amount_raw = request.POST.get("amount", "").strip()
        redirect_url = request.POST.get("redirect_url", "").strip() or os.getenv("CLIENT_URL", "http://localhost:5175")
        amount = int(amount_raw) if amount_raw.isdigit() else None

        if not charge_id or not otp:
            return HttpResponse("Missing charge or OTP", status=400)

        result = try_activate_billing_charge(
            charge_id=charge_id,
            tx_ref=tx_ref,
            org_id=org_id,
            tier=tier,
            rail=rail,
            amount=amount,
            otp_code=otp,
        )
        if result.get("activated"):
            body = f"""
  <h1>Payment confirmed</h1>
  <p class="success">Your {html.escape(tier)} subscription is now active.</p>
  <p style="margin-top:20px"><a class="btn" href="{html.escape(redirect_url)}">Go to dashboard</a></p>
"""
            return _page("Payment confirmed", body)

        body = f"""
  <p class="error">Payment still pending ({html.escape(result.get('status', 'pending'))}).</p>
  <p class="muted">Try OTP <strong>123456</strong> again or wait for MoMo approval.</p>
  <p style="margin-top:20px"><a class="btn" href="javascript:history.back()">Back</a></p>
"""
        return _page("Payment pending", body)


@method_decorator(csrf_exempt, name="dispatch")
class FlutterwavePayStatusView(View):
    """Poll charge status and activate subscription (local dev fallback for webhooks)."""

    def get(self, request):
        charge_id = request.GET.get("charge", "").strip()
        tx_ref = request.GET.get("tx_ref", "").strip()
        org_id = request.GET.get("org", "").strip()
        tier = request.GET.get("tier", "PRO").strip()
        rail = request.GET.get("rail", "MOBILE_MONEY").strip()
        amount_raw = request.GET.get("amount", "").strip()
        amount = int(amount_raw) if amount_raw.isdigit() else None

        if not charge_id or not tx_ref:
            return JsonResponse({"activated": False, "error": "missing charge or tx_ref"}, status=400)

        result = try_activate_billing_charge(
            charge_id=charge_id,
            tx_ref=tx_ref,
            org_id=org_id,
            tier=tier,
            rail=rail,
            amount=amount,
        )
        return JsonResponse(result)
