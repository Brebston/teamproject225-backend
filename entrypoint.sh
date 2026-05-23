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

python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='$ADMIN_MAIL').exists():
    User.objects.create_superuser('admin', '$ADMIN_MAIL', '$ADMIN_PASSWORD')
    print('Superuser created successfully.')
else:
    print('Superuser already exists. Skipping...')
"

exec "$@"

