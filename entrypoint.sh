#!/bin/sh

set -e

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done

python manage.py migrate --noinput

exec "$@"