#!/bin/sh

set -e

POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

while ! nc -z "$POSTGRES_HOST" "$POSTGRES_PORT"; do
  sleep 1
done

python manage.py migrate --noinput

python manage.py shell <<'EOF'
from django.contrib.sites.models import Site
from urllib.parse import urlparse
import os

site_id = int(os.getenv("SITE_ID", "1"))
frontend_url = os.getenv("FRONTEND_URL", "")
domain = os.getenv("SITE_DOMAIN", "")
if not domain:
    domain = urlparse(frontend_url).netloc or frontend_url
domain = domain or "localhost"
Site.objects.update_or_create(
    id=site_id,
    defaults={"domain": domain, "name": domain},
)
print(f"Site configured: {domain}")
EOF

exec "$@"
