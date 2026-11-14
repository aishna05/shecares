#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export DJANGO_SETTINGS_MODULE=shecares.settings
python manage.py migrate --noinput
python manage.py collectstatic --noinput
seed="$(python -c 'import django; django.setup(); from core.models import User; print("yes" if not User.objects.exists() else "no")')"
if [ "$seed" = "yes" ]; then
  python manage.py seed
fi
exec gunicorn shecares.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 1 --timeout 120
