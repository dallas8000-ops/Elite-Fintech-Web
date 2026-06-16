#!/bin/sh
set -e
cd /app
echo "Running migrations..."
python manage.py migrate --noinput
echo "Refreshing daily FX rates (if stale)..."
python manage.py refresh_market_rates || true
echo "Starting Daphne on port ${PORT:-8000}..."
exec daphne -b 0.0.0.0 -p "${PORT:-8000}" config.asgi:application
