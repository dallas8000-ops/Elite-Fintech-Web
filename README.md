# Elite Fintech Systems

Production-oriented, multi-tenant billing and operations platform for **East African fintech teams**.

Built with Django + React, this project supports regional onboarding, daily FX-based local pricing, real-time billing events, and infrastructure patterns that fit a fixed monthly VPS budget.

## Why this exists

Most billing products are card-first and US-centric. East African fintech teams need mobile money rails, local compliance context, and currency-aware pricing.

Elite Fintech Systems is designed for:

- PSPs and fintech startups serving Uganda, Kenya, Rwanda, and Tanzania
- Wallet and payment teams that need org-based RBAC and auditability
- Product teams that want hosted SaaS economics on a predictable VPS budget
- Regional go-to-market with daily exchange-rate-aware pricing

## Core capabilities

- Multi-tenant organizations with role-based access (`OWNER`, `ADMIN`, `MEMBER`, `VIEWER`)
- JWT authentication with organization-aware flows
- Country-aware onboarding for East Africa (`UG`, `KE`, `RW`, `TZ`)
- Billing plans with daily FX conversion from USD anchors to local currencies
- Real-time billing and payment activity over WebSockets
- Mobile-money-first routing (Flutterwave/Pesapal path), with Stripe as optional fallback for international or Euro-linked card flows
- Docker Compose deployment for fixed-cost hosting

## Implementation status (honest matrix)

| Area | Status | Notes |
|---|---|---|
| Multi-tenant auth + RBAC | Implemented | JWT with org context, owner/admin/member/viewer roles |
| East Africa onboarding | Implemented | Country + region validation for UG/KE/RW/TZ |
| Daily FX pricing engine | Implemented | USD anchors -> UGX/KES/RWF/TZS via stored snapshots |
| Real-time billing feed | Implemented | Django Channels WebSocket endpoint |
| Stripe checkout | Implemented (secondary) | Optional fallback for international card use-cases; not the primary EA rail |
| PayFast checkout (ZA legacy) | Implemented | Legacy South Africa flow only |
| Flutterwave checkout (EA) | Planned / partial | Provider path and config checks exist, full checkout flow is pending |
| Automated tests | Baseline implemented | Core auth/RBAC/pricing tests included; coverage is not complete |

## East Africa first, South Africa legacy

This repository now defaults to East Africa:

- `MARKET=EA` (default) for Uganda, Kenya, Rwanda, Tanzania
- `MARKET=ZA` remains available only as legacy compatibility mode
- Default onboarding country is `UG`

## Architecture

### Backend (`apps/backend`)

- Django 5 + DRF API
- JWT via `djangorestframework-simplejwt`
- Channels + Daphne for async/WebSocket events
- FX snapshots persisted in `FxRateSnapshot`
- Market pricing service computes VAT-inclusive local amounts from USD anchors

### Frontend (`apps/web`)

- React 19 + TypeScript + Vite
- Tailwind CSS v4 dark fintech UI
- Shared navbar and authenticated dashboard flow
- Landing page with country-by-country pricing and tier positioning

## Tech stack

| Layer | Tech |
|---|---|
| API | Django 5, DRF, SimpleJWT |
| Async / Real-time | Django Channels, Daphne, Redis |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4 |
| Payments | Stripe, PayFast (legacy ZA), Flutterwave (EA path/stubbed readiness) |
| Data | SQLite (dev), PostgreSQL (prod) |
| Infra | Docker Compose on VPS |

## Repository structure

```text
apps/
  backend/     Django API, auth, billing, organizations, webhooks
  web/         React dashboard and marketing site
docs/
  DEPLOYMENT.md
  HOSTING-BUDGET.md
  ENTERPRISE.md
docker-compose.yml
```

## Getting started (local development)

### 1) Backend setup

```bash
cd apps/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py refresh_market_rates
python manage.py seed_demo
python manage.py runserver 0.0.0.0:8000
```

### 2) Frontend setup

```bash
cd apps/web
npm install
npm run dev
```

Frontend: `http://localhost:5173`  
Backend API: `http://localhost:8000`

Demo login:

- Email: `demo@elitefintech.co.ug`
- Password: `demo1234`

## Environment configuration

Main backend config lives in `apps/backend/.env.example`.

### Regional + pricing variables

```env
MARKET=EA
DEFAULT_COUNTRY=UG

FX_PRICING_ENABLED=true
FX_API_URL=https://open.er-api.com/v6/latest/USD
FX_STALE_HOURS=24
PRICING_BASE_CURRENCY=usd

USD_PRICE_STARTER=12
USD_PRICE_PRO=35
USD_PRICE_ENTERPRISE=120
```

### Other key variables

- `DATABASE_URL` for local SQLite or PostgreSQL
- `CLIENT_URL` for frontend origin
- Stripe keys and plan IDs
- PayFast credentials (legacy ZA workflows)
- `PLATFORM_CNAME_TARGET` for domain linking flows

## Daily FX pricing model

Pricing is anchored in USD and converted daily to local market currencies:

- Starter: **$12**
- Pro: **$35**
- Enterprise: **$120**

Flow:

1. Fetch rates from `open.er-api.com` (base USD)
2. Persist snapshot with source + trading date
3. Convert anchors to UGX/KES/RWF/TZS
4. Apply VAT-inclusive local pricing output
5. Serve to frontend via billing region endpoints

Fallback rates are used if API calls fail, so pricing remains available.

## API overview

### Auth and organizations

- `POST /api/v1/auth/register/` - register user + organization
- `POST /api/v1/auth/login/` - JWT login

### Billing and market pricing

- `GET /api/v1/billing/plans/` - plan catalog
- `GET /api/v1/billing/rates/` - latest FX snapshot details
- `GET /api/v1/billing/region/` - regional metadata + localized plan pricing
- `POST /api/v1/billing/checkout/` - payment initiation route

### Platform capabilities

- `GET /api/v1/platform/capabilities/` - public tier/capability metadata
- `GET /api/v1/platform/setup/` - setup manifest (auth required)
- `POST /api/v1/platform/setup/apply/` - apply setup transfer (auth required)
- `POST /api/v1/platform/domains/verify/` - verify custom domain ownership

### Webhooks and real-time

- `POST /webhooks/stripe/`
- `POST /webhooks/payfast/`
- `WS /ws/billing/?token=<jwt>`

## Deployment (fixed monthly budget)

Target: predictable cost, no usage-spike surprise bills.

- Typical range: **$8 - $30 / month**
- Recommended hosts: Hetzner, Contabo, DigitalOcean, Vultr, Lightsail
- Deployment method: Docker Compose

```bash
cp .env.production.example .env
docker compose up -d --build
```

See:

- `docs/DEPLOYMENT.md`
- `docs/HOSTING-BUDGET.md`

## Operational commands

From `apps/backend`:

```bash
python manage.py migrate
python manage.py refresh_market_rates
python manage.py seed_demo
```

With Docker:

```bash
docker compose up -d --build
docker compose logs -f api
docker compose ps
```

## Roadmap priorities

- Complete Flutterwave checkout integration for EA
- Harden webhook verification and retry workflows
- Expand test coverage for pricing, regional validation, and checkout paths
- Expand tenant analytics and reconciliation tooling

## Security and compliance notes

- Use strong `SECRET_KEY`, production `ALLOWED_HOSTS`, and HTTPS-only deployment
- Rotate PSP/API secrets regularly
- Ensure least-privilege role assignment at tenant level
- Add audit logging and retention policy aligned with local regulations

## Contributing

1. Create a feature branch
2. Make focused changes
3. Run backend/frontend checks locally
4. Open a pull request with test notes and rollout considerations

## License

Proprietary - internal/commercial use unless explicitly relicensed by the repository owner.
