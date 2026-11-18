#!/bin/sh
set -eu
# Container-to-container origin, never browser-visible configuration.
# A character allowlist also rejects newlines before the line-oriented grep check.
case "$BACKEND_URL" in
  *[!A-Za-z0-9:/._-]*)
    echo 'BACKEND_URL contains invalid origin characters.' >&2
    exit 1
    ;;
esac
if ! printf '%s' "$BACKEND_URL" | grep -Eq '^https?://[A-Za-z0-9][A-Za-z0-9._-]*(:[0-9]{1,5})?$'; then
  echo 'BACKEND_URL must be an HTTP(S) origin with hostname and optional port.' >&2
  exit 1
fi
authority=${BACKEND_URL#*://}
case "$authority" in
  *:*)
    port=${authority##*:}
    if [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
      echo 'BACKEND_URL port must be between 1 and 65535.' >&2
      exit 1
    fi
    ;;
esac
