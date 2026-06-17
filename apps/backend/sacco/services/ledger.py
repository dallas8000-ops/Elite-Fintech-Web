from __future__ import annotations

from django.db.models import Sum

from sacco.models import LedgerEntry, LedgerEntryType, SaccoMember


def member_balance(member: SaccoMember) -> int:
    credits = (
        LedgerEntry.objects.filter(member=member, entry_type=LedgerEntryType.CREDIT).aggregate(
            total=Sum("amount_minor")
        )["total"]
        or 0
    )
    debits = (
        LedgerEntry.objects.filter(member=member, entry_type=LedgerEntryType.DEBIT).aggregate(
            total=Sum("amount_minor")
        )["total"]
        or 0
    )
    adjustments = (
        LedgerEntry.objects.filter(member=member, entry_type=LedgerEntryType.ADJUSTMENT).aggregate(
            total=Sum("amount_minor")
        )["total"]
        or 0
    )
    refunds = (
        LedgerEntry.objects.filter(member=member, entry_type=LedgerEntryType.REFUND).aggregate(
            total=Sum("amount_minor")
        )["total"]
        or 0
    )
    return credits - debits - refunds + adjustments


def post_ledger_entry(
    *,
    member: SaccoMember,
    entry_type: str,
    amount_minor: int,
    description: str,
    payment_intent=None,
    external_reference: str = "",
) -> LedgerEntry:
    current = member_balance(member)
    if entry_type in (LedgerEntryType.CREDIT, LedgerEntryType.ADJUSTMENT):
        balance_after = current + amount_minor
    elif entry_type in (LedgerEntryType.DEBIT, LedgerEntryType.REFUND):
        balance_after = current - amount_minor
    else:
        balance_after = current

    return LedgerEntry.objects.create(
        organization=member.organization,
        member=member,
        payment_intent=payment_intent,
        entry_type=entry_type,
        amount_minor=amount_minor,
        balance_after=balance_after,
        description=description,
        external_reference=external_reference,
    )
