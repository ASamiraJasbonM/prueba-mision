# Backup y recuperación (U3; controles U2 y señales U1)

Objetivos propuestos RTO4h/RPO24h; ver [BCP](BCP.md). Ensayar una copia autorizada
en base aislada, nunca probar restore destructivo en la demo/producción. Requiere
shell POSIX Linux/WSL, clientes PostgreSQL **misma versión mayor que servidor**,
GPG, curl, uv y entorno Python. Herramienta reproducible para servidor16:
`docker build -f ops/backup.Dockerfile -t datapulse-backup:verify .`.
Ese toolbox no es imagen de aplicación ni se publica.

Inyectar PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE y BACKUP_GPG_KEY desde
gestor de secretos. No pasar contraseñas en URL de argumentos ni activar `set -x`.
DATABASE_URL de Django debe apuntar al mismo destino confirmado durante restore.

```sh
# Fuente con PG* ya definidos; archivo UTC y SHA256 en backups/ (ignorado).
sh scripts/backup.sh
# BACKUP_BUCKET=s3://bucket/prefijo es opcional; requiere AWS CLI y permisos mínimos.
# Destino NUEVO aislado, creado de antemano con createdb, usuarios/clave restaurados.
export PGDATABASE=datapulse_restore_test
export RESTORE_CONFIRM_DATABASE=datapulse_restore_test
# Actualizar DATABASE_URL mediante gestor de secretos al mismo host/puerto/base.
# Iniciar backend temporal contra esta base y definir su HEALTH_URL.
export HEALTH_URL=http://127.0.0.1:18003/api/health/
sh scripts/restore.sh backups/datapulse-<UTC>.dump.gpg
```

restore.sh valida destino, SHA256 y autenticidad GPG antes de ejecutar pg_restore
--clean --if-exists --exit-on-error; luego migrate, check, verificar_auditoria y
health. `RESTORE_SEED_DEMO=true` es opcional solo en ensayo demo; en recuperación
real se mantiene false. Sin argumento descarga el último .dump.gpg del bucket y
su SHA256. Roles/grants deben aprovisionarse por separado (--no-owner/no-privileges).
Mantener el rol migrador separado del rol aplicación; volver a verificar grants
y trigger append-only después del restore.

No se incluye workflow programado con secretos ficticios. TODO bucket, KMS/secret
manager, retención, periodicidad y ensayo remoto; no hay destino externo autorizado.
Programación recomendada: backup diario, restauración de verificación semanal en
base efímera y suite PostgreSQL completa, sin apuntar tests a base real.

## Evidencia del ensayo

Fecha UTC 2026-11-18; Docker Desktop local, PostgreSQL16; bases exclusivas
datapulse_backup_source y datapulse_backup_restore. Dataset seed sintético, tres
usuarios, diez países y once filas de auditoría. Claves dummy fuera del repo.

Duración real exitosa: **22 segundos**, registrada por restore.sh en
tmp/security-restore.log (`ok=true`, auditoría checked=11). El primer intento con cliente17 contra servidor16 falló
por transaction_timeout; se corrigió el toolbox y se añadió guard de versión en
backup.sh. No se ignora el error de pg_restore ni se filtra el dump con sed.

La medición incluye descifrado, restore, migraciones/check/auditoría/health; no
incluye detección, aprobación ni aprovisionamiento. No demuestra RTO con volumen
de producción. Custodia de dump/claves según [FORENSE](FORENSE.md), incidentes
según [IR](IR.md); health es liveness y no verifica por sí solo la conectividad
DB: auditoría y consultas posteriores sí prueban lectura de datos.
