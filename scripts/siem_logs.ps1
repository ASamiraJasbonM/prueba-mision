# Run from repository root. Separate terminal; Ctrl+C stops only log capture.
New-Item -ItemType Directory -Force -Path tmp/siem | Out-Null
docker compose logs --follow --no-color --no-log-prefix backend db | Out-File -FilePath tmp/siem/services.log -Encoding utf8
