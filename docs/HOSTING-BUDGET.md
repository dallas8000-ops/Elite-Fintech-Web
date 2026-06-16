# Hosting on a fixed budget — max $30 USD/month

You want **predictable monthly cost**, not usage meters, tokens, or surprise bills.  
This app runs as **Docker Compose** on one VPS — that model fits fixed pricing perfectly.

**Avoid for this budget goal:** Railway, Render, Fly.io, Cloud Run, AWS Lambda, Vercel serverless — all usage- or seat-based and easy to overshoot.

---

## Best picks (flat monthly rate, under $30)

All prices are **fixed per month** unless you add optional backups. No per-request fees.

| Provider | Plan | Price/mo | RAM | Fits this app? |
|----------|------|--------|-----|----------------|
| **Hetzner Cloud** | CPX11 | **~€4.5 (~$5)** | 2 GB | Tight — demo/small traffic only |
| **Hetzner Cloud** | CPX21 | **~€8 (~$9)** | 4 GB | **Recommended** — full stack comfortable |
| **Contabo** | Cloud VPS S | **~€7 (~$8)** | 8 GB | Great value, EU datacenter |
| **DigitalOcean** | Basic Droplet | **$12** | 2 GB | Simple, predictable, good docs |
| **Vultr** | Regular Cloud | **$12** | 2 GB | Fixed tier, hourly cap = monthly max |
| **AWS Lightsail** | 2 GB bundle | **$12** | 2 GB | Fixed bundle (Cape Town region exists) |
| **AWS Lightsail** | 4 GB bundle | **$24** | 4 GB | Headroom for growth |
| **Hostinger** | KVM 1 | **~$5–7** | 4 GB | Budget option |
| **Truehost Africa** | VPS packages | **~$10–25** | varies | Optional; same Docker setup if you prefer a local provider |

**From Uganda:** Pick on **fixed price + RAM**, not datacenter location. A billing dashboard is not latency-sensitive — **Contabo or Hetzner in EU is the right default**.

---

## Recommended stack for ≤ $30 (one bill)

```
One VPS ($8–12/mo)
  └── docker compose
        ├── api      (Django + Daphne)
        ├── web      (React + nginx)
        ├── postgres
        └── redis
```

No separate database SaaS. No Redis add-on. No PaaS surcharges.

### Deploy (same on any VPS)

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
git clone <your-repo> && cd elite-fintech-systems
cp .env.production.example .env
# Set SECRET_KEY, POSTGRES_PASSWORD, CLIENT_URL, ALLOWED_HOSTS

docker compose up -d --build
```

HTTPS: free **Caddy** or **nginx + Let's Encrypt** on the same box — no extra service fee.

Domain: **`.ug`** or **`.com`** — registrar fee is separate (~$10–15/year), not hosting.

---

## Monthly budget breakdown (realistic)

| Item | Cost |
|------|------|
| VPS (Hetzner CPX21 or DO $12) | **$8–12** |
| Domain `.com` / `.ug` (amortized) | **~$1** |
| Backups (optional Hetzner snapshot) | **~$2** |
| **Total** | **~$11–15/mo** |

Well under **$30** with room for a **$24 Lightsail** upgrade if you need 4 GB RAM.

---

## What $30/month does *not* need to include

| You can skip | Why |
|--------------|-----|
| Managed Postgres (Supabase, RDS) | Postgres in Docker is enough to start |
| Managed Redis | Redis in Docker is enough |
| CDN | nginx serves static frontend fine at this scale |
| Separate API + web servers | One VPS runs both containers |
| Payment gateway hosting fees | PayFast/Flutterwave charge per txn, not hosting |

---

## Uganda-specific notes

| Topic | Reality |
|-------|---------|
| **Payments** | **MTN MoMo** & **Airtel Money** dominate — not PayFast (SA). Use **Flutterwave** or **Pesapal** when you go live (txn fees, not monthly hosting). |
| **Currency** | Bill in **UGX** locally; VPS is usually quoted in **USD**. |
| **Compliance** | Bank of Uganda + **Data Protection and Privacy Act 2019** — not POPIA/FICA (SA). |
| **Hosting region** | EU VPS is fine. Region only matters for compliance contracts, not day-to-day billing UI speed. |
| **Power/connectivity** | Host in a proper DC (Hetzner/DO/Truehost), not a office machine in Kampala. |

---

## Providers to skip (for your constraints)

| Provider | Why skip |
|----------|----------|
| Railway | Usage-based; bad Django experience |
| Render | Gets expensive; you already know |
| Fly.io | Usage-based; bills can vary |
| Heroku | Expensive tiers for Docker + Postgres |
| GCP/Azure default | Easy to enable metered services by mistake |

---

## Suggested choice

**Start here:** **Contabo Cloud VPS S (~$8/mo)** or **Hetzner CPX21 (~$9/mo)** + `docker compose`.

- Fixed invoice every month  
- Full control  
- Runs this Django + Channels + React stack  
- Stays **under $30** with domain and backups  

Do not overthink region. EU hosting from Uganda is normal for this type of app.

---

## Verify after deploy

```bash
curl https://api.yourdomain.com/health/
```

Should return JSON. If it does, you are live — on a fixed bill.
