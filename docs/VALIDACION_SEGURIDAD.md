# Entrega de seguridad por etapa — 2026-11-18 UTC

> Evidencia histórica del 18 de noviembre. Las salidas y límites se conservan sin
> reescribirlas. Para despliegue, UI y pruebas incorporadas después consultar
> [ESTADO_ACTUAL](ESTADO_ACTUAL.md) y el CI del commit vigente.

## Resultado global

94 pruebas: **94 aprobadas en PostgreSQL16, sin skips** (81,344 s); SQLite:
**92 aprobadas + los 2 skips originales** (29,939 s). No se modifica ninguna de
las 61 pruebas previas ni migraciones 0001/0002. Se añaden 33 pruebas.

| Verificación ejecutada | Resultado |
|---|---|
| check --deploy --fail-level WARNING, DEBUG=False, claves dummy y redirect=True | No issues; 0 silenced |
| makemigrations --check --dry-run | No changes detected |
| spectacular --validate --fail-on-warn --file docs/openapi.yaml | Exit0, sin avisos |
| scripts/check_numeric_policy.py | Sin FloatField/float()/datetime.now() en producción |
| pip-audit2.10.1 --strict --no-deps --disable-pip sobre export uv no-dev | No known vulnerabilities found |
| Bandit1.9.4 -r backend -ll, exclusión tests/migraciones | 0 MEDIUM/HIGH; 2 LOW fuera del umbral |
| Trivy0.76.2 imagen final, HIGH/CRITICAL, ignore-unfixed=true, exit-code1 | 0 hallazgos corregibles, exit0 |
| uv0.13.9 lock --check dentro de imagen final | Resolved67 packages, exit0 |
| id dentro de imagen | uid10001/gid10001 appuser |
| actionlint1.7.12 backend-ci.yml/frontend-ci.yml | Sin errores |
| verificar_auditoria sobre seed aislado PostgreSQL | ok=true, checked11 |
| verificar_auditoria sobre demo local migrada | ok=true, checked21 |
| Restauración cifrada PostgreSQL | ok=true, 22s, 3 usuarios/10 países/11 eventos |
| SIEM provisioning + scripts/verify_siem.py | 4 paneles, 5 reglas, 9 consultas válidas, muestra100 eventos |

La imagen final verificada tiene digest local manifest
`sha256:a919b1c9e8fcb57fa1190a239017dadf1972465cd4e9853def7740eba70c0b18`;
Trivy identifica config/imageID
`sha256:2161fcfd7e69d5b8643520de27122947392cf87488dff21308b8cc86ef79d8d4`.
No son publicaciones remotas. Fuente de evidencia técnica local: logs/informes
`tmp/security-*`, `tmp/audit-backend.json`, `tmp/trivy-backend-final.json` y
`tmp/security-bandit.json`, ignorados para no subir artefactos/datos innecesarios.

## Decisiones y archivos por etapa

| Etapa | Decisión / prueba | Archivos clave |
|---|---|---|
| 0 U2 | DRF3.18.2 corrige5 avisos; uv0.13.9 y SO corrigen7 hallazgos iniciales; scanners fallan ante regresión | pyproject.toml, uv.lock, Dockerfile, .bandit, .github/workflows/backend-ci.yml, .github/dependabot.yml, SECURITY.md |
| 1 U1/U2 | Axes DB, CAPTCHA local prod, scopes, idempotencia DB, blacklist y claves12+ | core/auth_api.py, security_auth.py, captcha_api.py, idempotency.py, test_security_auth.py, migración0004 |
| 2 U3 | Cadena canónica SHA/HMAC, lock singleton, backfill, PG trigger/revoke y admin lectura | core/audit.py, services/audit_chain.py, verificar_auditoria.py, migraciones0003/0006, test_audit_chain.py, test_audit_migration.py |
| 3 U2 | HSTS/cookies/CSP sidecar local, docs prod apagadas, preservar headers404 | config/settings.py, core/security_headers.py, security_schema.py, observability.py, test_security_headers.py |
| 4 U2/U3 | Runbooks específicos, responsables funcionales y límites medidos | SEGURIDAD.md, BCP.md, IR.md, FORENSE.md, RESTORE.md |
| 5 U1 | Alloy mantenido reemplaza Promtail EOL; sin socketDocker; reglas provisionadas | docker-compose.siem.yaml, ops/, scripts/build_siem_config.py, verify_siem.py, siem_logs.ps1, test_siem_contract.py |
| 6 U1 | MFA ADMIN opcional, retos/recovery únicos, sesión previa revocada | core/mfa_api.py, services/mfa.py, authentication.py, test_mfa.py, migración0005 |
| 7 U2 | Fernet, claves prod obligatorias, rotación transaccional | services/crypto.py, rotar_field_key.py, test_mfa.py, test_security_startup.py |
| 8 U3 | GPG AES256+SHA256, validación destino/versiones, restore real22s | scripts/backup.sh, restore.sh, ops/backup.Dockerfile, .gitattributes, RESTORE.md |
| 9 U2 | Fuente Angular revisada y checklist HTTPS/CORS; sin cambiar código frontend | SEGURIDAD_FRONTEND.md, INTEGRACION_SEGURIDAD.md, README.md |

El [índice consolidado](SEGURIDAD.md) contiene amenaza→medida→prueba→limitación,
referencias U1/U2/U3 y TODO operativos. Código completo revisable en los archivos
del árbol y en [snapshot de archivos clave](seguridad/CODIGO.md).

## Reproducción

Desde PowerShell con entorno local, `uv sync --frozen` y claves inyectadas cuando
DEBUG=False (no copiar los dummy de CI a producción):

```powershell
uv lock --check
uv sync --frozen
uv run python backend/manage.py check --deploy --fail-level WARNING
uv run python backend/manage.py makemigrations --check --dry-run
uv run python backend/manage.py test -v 2
uv run python backend/manage.py spectacular --validate --fail-on-warn --file docs/openapi.yaml
uv run python scripts/check_numeric_policy.py
uv export --frozen --no-dev --no-hashes --output-file tmp/requirements.audit.txt
uv run pip-audit -r tmp/requirements.audit.txt --strict --no-deps --disable-pip
uv run bandit -r backend -ll -x backend/core/migrations,backend/core/tests
uv run python backend/manage.py verificar_auditoria
```

La ejecución nativa usó `.venv\Scripts\python.exe`/scanners instalados con uv por
restricciones de resolución de rutas del sandbox Windows; la imagen comprobó el
lock con uv0.13.9. Nunca se instalaron dependencias del proyecto mediante pip.
Para pruebas CI: DEBUG=False, SECURE_SSL_REDIRECT=False, CAPTCHA_ENFORCED=False,
API_DOCS_ENABLED=True y las claves dummy documentadas en workflow. Para deploy
check usar SECURE_SSL_REDIRECT=True. No ejecutar check --deploy con DEBUG=True
y representar sus avisos como un fallo de producción.

Para Docker/SIEM/backup seguir [SIEM](SIEM.md) y [RESTORE](RESTORE.md). El filtro
anti-skips PostgreSQL del workflow permanece intacto. La imagen se transfiere
entre jobs por artifact, se escanea sin publicarla ni usar credenciales GHCR.

## Pendientes y límites explícitos

- No se ejecutó GitHub Actions remoto ni se hizo push/despliegue.
- No se aportaron PDFs U1/U2/U3: referencias temáticas del prompt, sin citas de
  página ni verificación de Tabla5. Contrastar con originales antes de defensa.
- No hay dominio/TLS, bucket ni contactos/on-call productivos; SECURITY.md conserva
  un email placeholder explícito. Validar configuración real antes de exponer.
- CAPTCHA/MFA no tienen UI Angular; no declarar integración productiva de esos
  flujos. La demo sin MFA y CAPTCHA conserva compatibilidad.
- DRF cache local limita por proceso, y proxy puede agrupar IP; falta cache
  compartida y una frontera de IP confiable en despliegue multiproceso.
- HMAC no impide a un administrador con DB+clave reescribir toda la historia;
  anclar manifiestos fuera del host y separar permisos/claves.
- Rotación de campos probada localmente; rotación HMAC versionada, S3, simulacros
  de volumen real, scheduler de backups/verificación y notificaciones pendientes.
- SIEM local no equivale a un servicio SOC ni evidencia WORM.

La demo SQLite se respaldó antes de migrar en tmp/pre-security-demo.sqlite3 y
su cadena fue verificada. Bases/servidores/volúmenes creados para ensayos se
eliminan al terminar; imágenes y reportes locales se conservan para revisión.
