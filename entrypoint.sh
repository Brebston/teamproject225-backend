#!/bin/sh

set -e

POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

while ! nc -z "$POSTGRES_HOST" "$POSTGRES_PORT"; do
  sleep 1
done


mkdir -p /app/static /app/media
chmod -R 755 /app/static /app/media

python manage.py migrate --noinput
python manage.py collectstatic --noinput

ADMIN_MAIL="${ADMIN_MAIL:-admin@example.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"

python manage.py createsuperuser --email "$ADMIN_MAIL" --password "$ADMIN_PASSWORD"

exec "$@"

