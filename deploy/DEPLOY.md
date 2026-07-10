# Deployment Guide

Platform: **Railway**
Framework: **Django + React**
Primary payments: **Flutterwave v4 OAuth** (East Africa MoMo)

## Pre-deploy checklist
1. Run readiness — aim for 80+ score (`/health/ready/`)
2. Set Flutterwave **client credentials** (not legacy `FLWSECK` keys):
   - `FLUTTERWAVE_CLIENT_ID`
   - `FLUTTERWAVE_CLIENT_SECRET`
   - `FLUTTERWAVE_ENV=sandbox` or `live`
   - `FLUTTERWAVE_WEBHOOK_SECRET`
3. Set `DATABASE_URL` and apply migrations
4. Set `CLIENT_URL` to the live frontend URL
5. Optional: Stripe keys only if you need international card fallback

## Environment variables (API service)
```
DEBUG=False
SECRET_KEY=<strong-random>
DATABASE_URL=${{elite-fintech-systems-db.DATABASE_URL}}
CLIENT_URL=https://<your-web-service>.up.railway.app
MARKET=EA
DEFAULT_COUNTRY=UG

FLUTTERWAVE_CLIENT_ID=<from Flutterwave dashboard>
FLUTTERWAVE_CLIENT_SECRET=<from Flutterwave dashboard>
FLUTTERWAVE_ENV=sandbox
FLUTTERWAVE_WEBHOOK_SECRET=<verif-hash secret>

# Optional card fallback
# STRIPE_SECRET_KEY=sk_live_...
# STRIPE_WEBHOOK_SECRET=whsec_...
```

## Deploy
```bash
railway up
```

## Post-deploy
1. Verify SSL and `GET /health/`
2. Confirm readiness shows Flutterwave configured
3. Register Flutterwave webhook → `https://<api>/webhooks/flutterwave/`
4. Smoke checkout: `POST /api/v1/billing/checkout/` with `rail=MOBILE_MONEY`
