# Railway — Elite Fintech Systems (one app)

Elite Fintech is **one app** in **one Railway project** (your shared portfolio project, e.g. `hearty-enjoyment`). Railway always uses multiple **services** inside that project for a full stack — that is normal and is not splitting the app.

| Service | Purpose | Root directory |
|---------|---------|----------------|
| `elite-fintech-systems-api` | Django API | `apps/backend` |
| `elite-fintech-systems-web` | React dashboard | `.` (Dockerfile `apps/web/Dockerfile`) |
| `elite-fintech-systems-db` | Postgres | plugin |

All three stay in the **same** Railway project as your other portfolio apps. Only the **service names** are normalized so Elite Fintech is easy to spot in the list.

## Rename only (no new project)

```bash
cd "C:\Software Projects\Deployment-Stripe-center\backend"
python manage.py railway_reconcile_portfolio --slug elite-fintech-systems --user dallas8000@gmail.com --rename
```

## If you accidentally created an empty "Elite Fintech Systems" project

Delete it in the Railway dashboard (Project settings → Delete). The live app should remain in your portfolio project.

## Not required

- A separate Railway project per app — **not needed** unless you want billing/isolation boundaries later.
- Merging api + web into one service — possible but worse for deploys; api/web/db as named services is the standard monorepo pattern.
