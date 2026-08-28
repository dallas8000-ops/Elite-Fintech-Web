# Django Model Reference
_Auto-generated from codebase scan._

## `RevokedRefreshToken`
**Module:** `apps/backend/accounts/models.py`
| Field | Type |
|-------|------|
| `jti` | CharField |
| `revoked_at` | DateTimeField |

## `FxRateSnapshot`
**Module:** `apps/backend/billing/models.py`
| Field | Type |
|-------|------|
| `id` | UUIDField |
| `base_currency` | CharField |
| `rates` | JSONField |
| `source` | CharField |
| `trading_date` | DateField |
| `fetched_at` | DateTimeField |

## `Subscription`
**Module:** `apps/backend/billing/models.py`
| Field | Type |
|-------|------|
| `id` | UUIDField |
| `organization` | OneToOneField |
| `external_subscription_id` | CharField |
| `external_price_id` | CharField |
| `payment_provider` | CharField |
| `plan_tier` | CharField |
| `status` | CharField |
| `amount_cents` | PositiveIntegerField |
| `currency` | CharField |
| `vat_cents` | PositiveIntegerField |
| `current_period_start` | DateTimeField |
| `current_period_end` | DateTimeField |
| `cancel_at_period_end` | BooleanField |
| `created_at` | DateTimeField |
| `updated_at` | DateTimeField |

## `PaymentEvent`
**Module:** `apps/backend/billing/models.py`
| Field | Type |
|-------|------|
| `id` | UUIDField |
| `organization` | ForeignKey |
| `type` | CharField |
| `amount` | PositiveIntegerField |
| `vat_amount` | PositiveIntegerField |
| `currency` | CharField |
| `payment_provider` | CharField |
| `payment_rail` | CharField |
| `settlement_status` | CharField |
| `external_event_id` | CharField |
| `metadata` | JSONField |
| `created_at` | DateTimeField |

## `OrganizationDomain`
**Module:** `apps/backend/efs_platform/models.py`
| Field | Type |
|-------|------|
| `id` | UUIDField |
| `organization` | ForeignKey |
| `hostname` | CharField |
| `domain_type` | CharField |
| `status` | CharField |
| `verification_token` | CharField |
| `verified_at` | DateTimeField |
| `is_primary` | BooleanField |
| `created_at` | DateTimeField |

## `SetupTransfer`
**Module:** `apps/backend/efs_platform/models.py`
| Field | Type |
|-------|------|
| `id` | UUIDField |
| `organization` | OneToOneField |
| `transfer_token` | CharField |
| `target_domain` | CharField |
| `api_subdomain` | CharField |
| `app_subdomain` | CharField |
| `automation_agent` | CharField |
| `completed_steps` | JSONField |
| `metadata` | JSONField |
| `created_at` | DateTimeField |
| `updated_at` | DateTimeField |

## `Organization`
**Module:** `apps/backend/organizations/models.py`
| Field | Type |
|-------|------|
| `id` | UUIDField |
| `name` | CharField |
| `slug` | SlugField |
| `cipc_registration_number` | CharField |
| `vat_number` | CharField |
| `province` | CharField |
| `country` | CharField |
| `industry_sector` | CharField |
| `popia_consent_at` | DateTimeField |
| `fica_status` | CharField |
| `fica_verified_at` | DateTimeField |
| `stripe_customer_id` | CharField |
| `payfast_token` | CharField |
| `created_at` | DateTimeField |
| `updated_at` | DateTimeField |

## `Membership`
**Module:** `apps/backend/organizations/models.py`
| Field | Type |
|-------|------|
| `id` | UUIDField |
| `user` | ForeignKey |
| `organization` | ForeignKey |
| `role` | CharField |
| `created_at` | DateTimeField |

## `SaccoMember`
**Module:** `apps/backend/sacco/models.py`
| Field | Type |
|-------|------|
| `id` | UUIDField |
| `organization` | ForeignKey |
| `member_number` | CharField |
| `full_name` | CharField |
| `phone` | CharField |
| `momo_network` | CharField |
| `status` | CharField |
| `joined_at` | DateField |
| `metadata` | JSONField |
| `created_at` | DateTimeField |
| `updated_at` | DateTimeField |

## `CollectionProduct`
**Module:** `apps/backend/sacco/models.py`
| Field | Type |
|-------|------|
| `id` | UUIDField |
| `organization` | ForeignKey |
| `name` | CharField |
| `amount_minor` | PositiveIntegerField |
| `currency` | CharField |
| `frequency` | CharField |
| `vat_inclusive` | BooleanField |
| `is_active` | BooleanField |
| `created_at` | DateTimeField |
| `updated_at` | DateTimeField |

## `PaymentIntent`
**Module:** `apps/backend/sacco/models.py`
| Field | Type |
|-------|------|
| `id` | UUIDField |
| `idempotency_key` | CharField |
| `organization` | ForeignKey |
| `member` | ForeignKey |
| `product` | ForeignKey |
| `amount_minor` | PositiveIntegerField |
| `currency` | CharField |
| `rail` | CharField |
| `provider` | CharField |
| `status` | CharField |
| `provider_reference` | CharField |
| `provider_transaction_id` | CharField |
| `phone` | CharField |
| `purpose` | CharField |
| `expires_at` | DateTimeField |
| `metadata` | JSONField |
| `created_by` | ForeignKey |
| `created_at` | DateTimeField |
| `updated_at` | DateTimeField |

## `LedgerEntry`
**Module:** `apps/backend/sacco/models.py`
| Field | Type |
|-------|------|
| `id` | UUIDField |
| `organization` | ForeignKey |
| `member` | ForeignKey |
| `payment_intent` | ForeignKey |
| `entry_type` | CharField |
| `amount_minor` | PositiveIntegerField |
| `balance_after` | IntegerField |
| `description` | CharField |
| `external_reference` | CharField |
| `created_at` | DateTimeField |
