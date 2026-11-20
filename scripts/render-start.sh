#!/bin/sh
set -eu
# Render Free has no Shell/pre-deploy command. Migrate before accepting traffic.
# Seed is a separate one-time operation and is never run on restart.
python backend/manage.py migrate --noinput
exec gunicorn scripts.render_wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 2 --timeout 60 --forwarded-allow-ips=127.0.0.1
