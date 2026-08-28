# Domain & SSL Setup

Production URL: https://elite-fintech-api-production.up.railway.app
Domain: elite-fintech-api-production.up.railway.app
Framework: django

## SSL
SSL/TLS is automatic on Vercel, Railway, and Fly.io custom domains.

## Stripe Webhook (production)
Update webhook URL to: `https://elite-fintech-api-production.up.railway.app/webhooks/stripe/`

## Verification
```bash
curl https://elite-fintech-api-production.up.railway.app/health/
```
Run readiness from Stripe Installer after deploy.
