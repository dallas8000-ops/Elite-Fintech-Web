# Generated for daily FX pricing

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0002_paymentevent_settlement_status_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="FxRateSnapshot",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("base_currency", models.CharField(default="usd", max_length=3)),
                ("rates", models.JSONField(default=dict)),
                ("source", models.CharField(max_length=128)),
                ("trading_date", models.DateField()),
                ("fetched_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "fx_rate_snapshots",
                "ordering": ["-fetched_at"],
            },
        ),
    ]
