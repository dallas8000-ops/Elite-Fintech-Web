# Enterprise tier & domain setup

## What tier is this?

**ENTERPRISE** — not Basic or Pro.

| | Basic SaaS | Pro SaaS | **Elite Fintech (this app)** |
|---|------------|----------|------------------------------|
| Payments | Card only | + PayFast | **Rail-first African** (EFT, PayShap, DebiCheck) |
| Tenancy | Single | Multi-tenant | **Multi-tenant + org JWT** |
| Compliance | — | Partial | **POPIA, FICA, CIPC, VAT** |
| Real-time | — | Webhooks | **Django Channels live feed** |
| Custom domain | — | — | **api + app subdomains** |
| AI automation | — | — | **Setup Transfer API** |

Verify publicly (no auth):

```bash
curl http://localhost:8000/api/v1/platform/capabilities/
```

## Link your domain (AI automation supported)

The **Setup Transfer API** is built for Cursor, GitHub Actions, Terraform, or any agent that can call REST + apply DNS/env output.

### 1. Authenticate

```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@elitefintech.co.za","password":"demo1234"}'
```

Save the `token` from the response.

### 2. Apply setup transfer

```bash
curl -X POST http://localhost:8000/api/v1/platform/setup/apply/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "target_domain": "yourcompany.co.za",
    "automation_agent": "cursor"
  }'
```

Response includes:

- `urls.api_production` → `https://api.yourcompany.co.za`
- `urls.app_production` → `https://app.yourcompany.co.za`
- `dns_records` → CNAME + TXT to add at your registrar
- `environment` → copy into production `.env`
- `webhook_urls` → register at PayFast / Stripe
- `transfer_token` → for subsequent automation calls

### 3. Add DNS at your registrar

| Type | Host | Value |
|------|------|-------|
| CNAME | api | `edge.elitefintech.systems` (or your edge) |
| CNAME | app | `edge.elitefintech.systems` |
| TXT | `_elite-verify` | `elite-verify=<token from API>` |

### 4. Verify domain

```bash
curl -X POST http://localhost:8000/api/v1/platform/domains/verify/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"hostname":"api.yourcompany.co.za","verification_token":"TOKEN_FROM_DNS"}'
```

### 5. Deploy with returned environment

```env
CLIENT_URL=https://app.yourcompany.co.za
ALLOWED_HOSTS=api.yourcompany.co.za,app.yourcompany.co.za
VITE_API_URL=https://api.yourcompany.co.za
VITE_WS_URL=wss://api.yourcompany.co.za/ws/billing/
```

## UI setup wizard

After login: **Dashboard → Domain setup** (`/setup`)

## OpenAPI for agents

```
GET /api/v1/platform/openapi/
```

## Cursor automation example

In Cursor, you can prompt:

> Call GET /api/v1/platform/setup/ with my JWT, apply target_domain mybrand.co.za, output DNS records and production .env

The API returns a machine-readable manifest designed for this workflow.
