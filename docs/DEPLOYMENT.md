# Deployment — fixed monthly budget (≤ $30 USD)

**Set rate only — no tokens, no usage meters.**

→ Full provider list and Uganda notes: **[HOSTING-BUDGET.md](HOSTING-BUDGET.md)**

| Pick | Fixed price |
|------|-------------|
| **Hetzner CPX21** | ~**$9/mo** |
| **DigitalOcean / Vultr** | **$12/mo** |
| **AWS Lightsail** | **$12–24/mo** |
| **Contabo VPS S** | ~**$8/mo** |

One VPS runs the entire stack via `docker compose` (API, web, Postgres, Redis).

No Railway. No Render required.

---

## Deploy

```bash
# Ubuntu 22.04+ VPS
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
git clone <your-repo> && cd elite-fintech-systems
cp .env.production.example .env
# Edit: SECRET_KEY, POSTGRES_PASSWORD, CLIENT_URL, ALLOWED_HOSTS

docker compose up -d --build
docker compose exec api python manage.py seed_demo   # optional
```

| Service | Port | Public URL |
|---------|------|------------|
| Dashboard | 8080 | `https://app.yourdomain.com` |
| API | 8000 | `https://api.yourdomain.com` |

Point **Caddy** or **nginx** at those ports for free HTTPS. Use `/setup` in the app for DNS/env manifest.

---

## Skip (not fixed-rate friendly)

| Platform | Why |
|----------|-----|
| Railway | Usage-based + Django pain |
| Render | Expensive at scale |
| Fly.io | Usage-based bills vary |
| Cloud Run / Lambda | Per-request pricing |

---

## Production checklist

- [ ] `DEBUG=False`
- [ ] Strong `SECRET_KEY`
- [ ] `CLIENT_URL` matches your live app URL
- [ ] `ALLOWED_HOSTS` includes API hostname
- [ ] Payment webhooks → `https://api.yourdomain.com/webhooks/...`
- [ ] Firewall: only 80/443 public

```bash
curl https://api.yourdomain.com/health/
```

---

## From Uganda

- **Contabo or Hetzner (EU)** — fixed ~$8–9/mo. Latency is not a concern for billing/admin work.
- Payments at go-live: **MTN MoMo / Flutterwave** — not PayFast (South Africa).
