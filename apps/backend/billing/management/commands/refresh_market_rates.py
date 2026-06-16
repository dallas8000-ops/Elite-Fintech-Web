from django.core.management.base import BaseCommand

from billing.services.fx_rates import refresh_market_rates, rates_public_payload


class Command(BaseCommand):
    help = "Fetch daily FX rates from market API and update pricing snapshots"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Refresh even if the latest snapshot is still fresh",
        )

    def handle(self, *args, **options):
        snap = refresh_market_rates(force=options["force"])
        payload = rates_public_payload(snap)
        self.stdout.write(self.style.SUCCESS("Market rates updated"))
        self.stdout.write(f"  Source:       {payload['source']}")
        self.stdout.write(f"  Trading date: {payload.get('trading_date')}")
        self.stdout.write(f"  Base:         {payload['base_currency']}")
        for cur, rate in sorted(payload.get("rates", {}).items()):
            self.stdout.write(f"  {cur}: {rate}")
