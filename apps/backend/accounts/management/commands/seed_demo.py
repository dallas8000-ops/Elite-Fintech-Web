from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from billing.models import PaymentEvent, PaymentEventType, PaymentProvider, SettlementStatus
from organizations.models import Membership, Organization, Role


class Command(BaseCommand):
    help = "Seed demo East African fintech organization with mobile money events"

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(
            email="demo@elitefintech.co.ug",
            defaults={"name": "Amina Nakato"},
        )
        user.set_password("demo1234")
        user.save()

        org, _ = Organization.objects.get_or_create(
            slug="kampala-pay",
            defaults={
                "name": "Kampala Pay Ltd",
                "country": "UG",
                "province": "CENTRAL",
                "industry_sector": "Payments & Wallets",
                "cipc_registration_number": "80020012345678",
                "vat_number": "1000123456",
                "popia_consent_at": timezone.now(),
            },
        )

        Membership.objects.get_or_create(
            user=user,
            organization=org,
            defaults={"role": Role.OWNER},
        )

        demo_events = [
            {
                "external_event_id": "demo_momo_001",
                "type": PaymentEventType.INVOICE_PAID,
                "amount": 180_000,
                "rail": "MOBILE_MONEY",
                "settlement": SettlementStatus.SETTLED,
                "metadata": {"wallet": "MTN MoMo", "note": "UGX subscription — instant wallet debit"},
            },
            {
                "external_event_id": "demo_ussd_001",
                "type": PaymentEventType.INVOICE_PAID,
                "amount": 550_000,
                "rail": "USSD",
                "settlement": SettlementStatus.SETTLED,
                "metadata": {"session": "*165#", "note": "USSD payment — no smartphone required"},
            },
            {
                "external_event_id": "demo_agent_001",
                "type": PaymentEventType.PAYMENT_SUCCEEDED,
                "amount": 45_000,
                "rail": "AGENT_CASH",
                "settlement": SettlementStatus.SETTLED,
                "metadata": {"agent": "Kampala agent", "note": "Cash-in at agent counter"},
            },
            {
                "external_event_id": "demo_momo_pending_001",
                "type": PaymentEventType.EFT_PENDING,
                "amount": 120_000,
                "rail": "MOBILE_MONEY",
                "settlement": SettlementStatus.PENDING,
                "metadata": {"wallet": "Airtel Money", "note": "Awaiting telco confirmation"},
            },
        ]

        for ev in demo_events:
            PaymentEvent.objects.get_or_create(
                external_event_id=ev["external_event_id"],
                defaults={
                    "organization": org,
                    "type": ev["type"],
                    "amount": ev["amount"],
                    "vat_amount": round(ev["amount"] * 18 / 118),
                    "currency": "ugx",
                    "payment_provider": PaymentProvider.PAYFAST,
                    "payment_rail": ev["rail"],
                    "settlement_status": ev["settlement"],
                    "metadata": ev["metadata"],
                },
            )

        self.stdout.write(self.style.SUCCESS("Seed complete"))
        self.stdout.write("  Email:    demo@elitefintech.co.ug")
        self.stdout.write("  Password: demo1234")
        self.stdout.write(f"  Org:      {org.name} ({org.slug}) — Uganda")
        self.stdout.write(f"  Events:   {len(demo_events)} East Africa MoMo demo transactions")
