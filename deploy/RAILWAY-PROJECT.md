# Railway — Elite Fintech Systems layout

Elite Fintech should appear as **one dedicated Railway project**, not mixed with other portfolio apps.

## Target layout

| Railway project | Service | Root directory | Public URL |
|-----------------|---------|----------------|------------|
| **Elite Fintech Systems** | `elite-fintech-systems-api` | `apps/backend` | `elite-fintech-api-production.up.railway.app` |
| | `elite-fintech-systems-web` | `.` (repo root) | `elite-fintech-web-production.up.railway.app` |
| | `elite-fintech-systems-db` | Postgres plugin | (internal) |

## Fix a cluttered dashboard

If API, web, and Postgres appear inside a shared hub project with Kistie, SilverFox, etc.:

1. **Create** a new Railway project named `Elite Fintech Systems`.
2. **Connect** the same GitHub repo twice:
   - Service `elite-fintech-systems-api` → root `apps/backend`
   - Service `elite-fintech-systems-web` → root `.` → Dockerfile `apps/web/Dockerfile`
3. **Add** Postgres → rename to `elite-fintech-systems-db`.
4. **Copy env vars** from the old services (or run from Deployment-Stripe-center):
   ```bash
   python manage.py stripe_installer deploy elite-fintech-systems --push --user you@email.com
   ```
5. **Set** `PLATFORM_TIER=PLATINUM`, `CLIENT_URL`, `DEBUG=False` on the API service.
6. **Redeploy** API and web; verify `/health/` and `/api/v1/platform/capabilities/`.
7. **Remove** legacy cards from the hub project: `Elite-Fintech-Web`, `elite-fintech-api`, `Postgres-Fintech`.

## Automation audit (rename + report)

From Deployment-Stripe-center:

```bash
python manage.py railway_reconcile_portfolio --slug elite-fintech-systems --user dallas8000@gmail.com
python manage.py railway_reconcile_portfolio --slug elite-fintech-systems --rename
```

`--rename` applies canonical service names via the Railway API. Use `--create-project` to ensure a dedicated project exists.
