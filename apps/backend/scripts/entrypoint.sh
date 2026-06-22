#!/bin/sh
set -e
cd /app

echo "Running migrations..."
python manage.py migrate --noinput

if [ "${SEED_DEMO}" = "true" ]; then
  echo "Seeding demo data..."
  python manage.py seed_demo || true
fi

echo "Starting Daphne on port ${PORT:-8000}..."
# Non-blocking: do not delay Railway healthcheck
( python manage.py refresh_market_rates || true ) &

exec daphne -b 0.0.0.0 -p "${PORT:-8000}" config.asgi:application
