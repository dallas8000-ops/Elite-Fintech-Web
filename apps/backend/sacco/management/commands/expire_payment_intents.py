from django.core.management.base import BaseCommand

from sacco.services.intents import expire_stale_intents


class Command(BaseCommand):
    help = "Mark pending payment intents past expiry as EXPIRED"

    def handle(self, *args, **options):
        count = expire_stale_intents()
        self.stdout.write(self.style.SUCCESS(f"Expired {count} payment intent(s)"))
