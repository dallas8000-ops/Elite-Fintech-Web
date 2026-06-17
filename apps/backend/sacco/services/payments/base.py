from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol


@dataclass
class ChargeResult:
    provider_reference: str
    status: str
    message: str
    payment_url: str | None = None
    provider_transaction_id: str | None = None
    raw: dict | None = None


class PaymentProviderAdapter(Protocol):
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
    ) -> ChargeResult: ...

    def verify_transaction(self, transaction_id: str) -> dict: ...
