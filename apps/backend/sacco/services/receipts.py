from __future__ import annotations

from billing.services.regional import extract_vat_from_inclusive, vat_rate
from sacco.models import PaymentIntent


def build_receipt(intent: PaymentIntent) -> dict:
    org = intent.organization
    member = intent.member
    country = org.country or "UG"
    rate = vat_rate(country)
    ex_vat, vat_amount = extract_vat_from_inclusive(intent.amount_minor, country)

    lines = [
        org.name,
        "—" * 32,
        f"Member: {member.full_name} ({member.member_number})",
        f"Phone: {intent.phone}",
        f"Purpose: {intent.purpose or 'Collection'}",
        f"Amount: USh {intent.amount_minor:,}",
    ]
    if rate > 0:
        lines.append(f"VAT ({int(rate * 100)}% inclusive): USh {vat_amount:,}")
        lines.append(f"Ex-VAT: USh {ex_vat:,}")
    lines.extend(
        [
            f"Reference: {intent.provider_reference}",
            f"MoMo txn: {intent.provider_transaction_id or '—'}",
            f"Status: {intent.status}",
            f"Date: {intent.updated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            "—" * 32,
            "Thank you for your contribution.",
        ]
    )
    text = "\n".join(lines)

    return {
        "organization": org.name,
        "member_name": member.full_name,
        "member_number": member.member_number,
        "amount_minor": intent.amount_minor,
        "currency": intent.currency,
        "vat_amount_minor": vat_amount,
        "purpose": intent.purpose,
        "provider_reference": intent.provider_reference,
        "provider_transaction_id": intent.provider_transaction_id,
        "status": intent.status,
        "paid_at": intent.updated_at.isoformat(),
        "text": text,
    }
