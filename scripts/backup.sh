#!/bin/sh
set -eu
umask 077
: "${PGDATABASE:?Set PGDATABASE, PGHOST, PGUSER and PGPASSWORD securely}"
: "${BACKUP_GPG_KEY:?Set BACKUP_GPG_KEY outside source control}"
destination=${BACKUP_DIR:-backups}
mkdir -p "$destination"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM
stamp=$(date -u +%Y%m%dT%H%M%SZ)
name="datapulse-$stamp.dump.gpg"
test ! -e "$destination/$name"
pg_dump --format=custom --no-owner --no-privileges --file="$work/database.dump"
printf '%s\n' "$BACKUP_GPG_KEY" | gpg --batch --yes --pinentry-mode loopback \
  --passphrase-fd 0 --symmetric --cipher-algo AES256 --output "$work/$name" "$work/database.dump"
(cd "$work" && sha256sum "$name" > "$name.sha256")
mv "$work/$name" "$destination/$name"
mv "$work/$name.sha256" "$destination/$name.sha256"
if [ -n "${BACKUP_BUCKET:-}" ]; then
  case "$BACKUP_BUCKET" in s3://*) ;; *) echo 'BACKUP_BUCKET must start with s3://' >&2; exit 1;; esac
  command -v aws >/dev/null
  aws s3 cp "$destination/$name" "${BACKUP_BUCKET%/}/$name" --only-show-errors
  aws s3 cp "$destination/$name.sha256" "${BACKUP_BUCKET%/}/$name.sha256" --only-show-errors
fi
printf 'Backup cifrado: %s/%s\n' "$destination" "$name"
