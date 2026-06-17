#!/bin/sh
set -e
cd /app
echo "Running migrations..."
python manage.py migrate --noinput
if [ "${SEED_DEMO:-auto}" != "false" ]; then
  if [ "${SEED_DEMO}" = "true" ] || [ -n "${RAILWAY_ENVIRONMENT}" ]; then
    echo "Seeding demo data..."
    python manage.py seed_demo || true
  fi
fi
echo "Refreshing daily FX rates (if stale)..."
python manage.py refresh_market_rates || true
echo "Starting Daphne on port ${PORT:-8000}..."
exec daphne -b 0.0.0.0 -p "${PORT:-8000}" config.asgi:application
