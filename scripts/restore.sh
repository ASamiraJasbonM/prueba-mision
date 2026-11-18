#!/bin/sh
set -eu
umask 077
: "${PGDATABASE:?Set the isolated target PGDATABASE}"
: "${RESTORE_CONFIRM_DATABASE:?Explicitly confirm the target database name}"
: "${BACKUP_GPG_KEY:?Set BACKUP_GPG_KEY outside source control}"
: "${HEALTH_URL:?Set the restored backend health URL}"
[ "$PGDATABASE" = "$RESTORE_CONFIRM_DATABASE" ] || { echo 'Target confirmation mismatch' >&2; exit 1; }
started=$(date +%s)
# Refuse to migrate/verify a different database from the restore destination.
uv run --frozen python backend/manage.py shell -c "import os; from django.conf import settings; d=settings.DATABASES['default']; assert d['ENGINE']=='django.db.backends.postgresql' and d['NAME']==os.environ['PGDATABASE'] and d['HOST']==os.environ.get('PGHOST','') and str(d.get('PORT') or 5432)==os.environ.get('PGPORT','5432'), 'Django and PG restore destinations differ'"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM
archive=${1:-}
if [ -z "$archive" ]; then
  : "${BACKUP_BUCKET:?Provide an archive path or BACKUP_BUCKET}"
  case "$BACKUP_BUCKET" in s3://*) ;; *) exit 1;; esac
  name=$(aws s3 ls "${BACKUP_BUCKET%/}/" | awk '/datapulse-[0-9]+T[0-9]+Z.dump.gpg$/ {print $4}' | sort | tail -n 1)
  [ -n "$name" ] || { echo 'No backup found' >&2; exit 1; }
  printf '%s\n' "$name" | grep -Eq '^datapulse-[0-9]{8}T[0-9]{6}Z\.dump\.gpg$' || { echo 'Invalid backup object name' >&2; exit 1; }
  aws s3 cp "${BACKUP_BUCKET%/}/$name" "$work/$name" --only-show-errors
  aws s3 cp "${BACKUP_BUCKET%/}/$name.sha256" "$work/$name.sha256" --only-show-errors
else
  name=$(basename "$archive")
  cp "$archive" "$work/$name"
  cp "$archive.sha256" "$work/$name.sha256"
fi
# Validate exactly this archive, never paths embedded in an untrusted manifest.
expected=$(awk 'NR==1 {print $1}' "$work/$name.sha256")
actual=$(sha256sum "$work/$name" | awk '{print $1}')
[ "${#expected}" -eq 64 ] && [ "$expected" = "$actual" ] || { echo 'SHA256 mismatch' >&2; exit 1; }
printf '%s\n' "$BACKUP_GPG_KEY" | gpg --batch --yes --pinentry-mode loopback \
  --passphrase-fd 0 --decrypt --output "$work/database.dump" "$work/$name"
pg_restore --exit-on-error --clean --if-exists --no-owner --no-privileges --dbname="$PGDATABASE" "$work/database.dump"
# Run from the repo root in an environment with uv and PostgreSQL client tools.
uv run --frozen python backend/manage.py migrate --noinput
if [ "${RESTORE_SEED_DEMO:-false}" = true ]; then
  uv run --frozen python backend/manage.py seed_data
fi
uv run --frozen python backend/manage.py check
uv run --frozen python backend/manage.py verificar_auditoria
curl --fail --silent --show-error "$HEALTH_URL" >/dev/null
elapsed=$(( $(date +%s) - started ))
printf '{"event":"restore_verification","ok":true,"duration_seconds":%s}\n' "$elapsed"
