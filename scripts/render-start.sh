#!/bin/sh
set -eu
# Render Free has no Shell/pre-deploy command. Migrate before accepting traffic.
# Seed is a separate one-time operation and is never run on restart.
python backend/manage.py migrate --noinput
exec python scripts/serve_backend.py
