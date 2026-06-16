from datetime import date

from django.test import TestCase

from billing.models import FxRateSnapshot
from billing.services.market_pricing import plans_for_country_market, usd_to_minor


class MarketPricingTests(TestCase):
    def setUp(self):
        FxRateSnapshot.objects.create(
            base_currency="usd",
            rates={"ugx": 3800, "kes": 130, "rwf": 1300, "tzs": 2600},
            source="test-fixture",
            trading_date=date.today(),
        )

    def test_usd_to_minor_rounds_kes_to_cents(self):
        # 12 USD * 130 = 1560 KES -> rounded in major, returned as minor (cents)
        amount = usd_to_minor(12, "kes", rate=130)
        self.assertEqual(amount, 155000)

    def test_plans_for_country_market_returns_ea_tiers_with_fx_metadata(self):
        plans, meta = plans_for_country_market("UG")

        self.assertEqual(len(plans), 3)
        self.assertEqual({p["tier"] for p in plans}, {"STARTER", "PRO", "ENTERPRISE"})
        self.assertEqual(meta["country"], "UG")
        self.assertEqual(meta["currency"], "ugx")
        self.assertEqual(meta["fx_rate"], 3800.0)
        self.assertIn("trading_date", meta)

    def test_invalid_country_falls_back_to_default_country(self):
        plans, meta = plans_for_country_market("XX")

        self.assertEqual(len(plans), 3)
        self.assertEqual(meta["country"], "UG")
