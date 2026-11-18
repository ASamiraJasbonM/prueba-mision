# Seguridad del backend DataPulse Latam

## Alcance y fuentes

Implementación incremental sobre el backend existente. No se modifican las
migraciones 0001/0002, las pruebas previas ni las reglas económicas (Decimal,
UTC y control de versión If-Match). No se publican imágenes ni se despliega.

U1 = monitoreo/logs/correlación/MFA; U2 = vulnerabilidades/respuesta/cifrado;
U3 = evidencia/continuidad/restauración. Estas referencias proceden del prompt:
**los tres PDFs U1/U2/U3 no están adjuntos**. No se atribuyen citas, páginas ni
el contenido exacto de la Tabla 5 sin leer los originales. TODO: contrastar la
matriz y la tabla de BCP con los PDFs cuando estén disponibles.

## 0. Baseline CI y dependencias (U2)

| Amenaza | Medida | Prueba ejecutable | Límite |
|---|---|---|---|
| Configuración insegura | check --deploy con DEBUG=False y TLS obligatorio | paso Production deployment checks | No verifica el certificado del despliegue |
| CVE Python | uv.lock + pip-audit --strict sobre export no-dev | job lint-and-check | Base de avisos depende de disponibilidad/fecha |
| Patrones inseguros | Bandit -ll; producción sin B101 desactivado | .bandit y CI | SAST no sustituye revisión |
| CVE imagen | Trivy HIGH/CRITICAL exit 1, imagen transferida como artifact | security-scan necesita docker-build | ignore-unfixed=true excluye sin parche; revisar informe completo |
| Dependencias abandonadas | Dependabot semanal Python/Actions/Docker | .github/dependabot.yml | Propuestas requieren revisión y pruebas |

DRF se actualiza de 3.16.1 a 3.18.2 por cinco avisos detectados por pip-audit
(PYSEC-2026-3827, PYSEC-2026-3828, CVE-2026-114136/114137/114138).
uv pasa de 0.10.11 a 0.13.9 por hallazgos del binario en Trivy. Se aplican
actualizaciones del sistema base en runtime; appuser, healthcheck y CMD siguen.
django-simple-captcha requiere construir el paquete pequeño django-ranged-response:
se elimina --no-build únicamente del builder; herramientas de compilación/dev
no se copian al runtime. pip-audit pertenece a dev; usa --no-deps --disable-pip
porque el export ya contiene todos los pins; no instala el proyecto mediante pip.

Parcheo: HIGH/CRITICAL ≤7 días, restantes ≤30 días o siguiente ventana con
responsable, justificación y vencimiento. No hay allowlist de CVEs.

## 1. Autenticación (U1/U2)

| Amenaza | Medida | Prueba | Límite |
|---|---|---|---|
| Fuerza bruta | Axes DB, email normalizado+REMOTE_ADDR, 5 fallos, 15 min | test_five_failures_then_lockout_audited | Ataques distribuidos requieren MFA/controles perimetrales |
| Evasión con XFF | Se ignora X-Forwarded-For; NUM_PROXIES=0 | test_lockout_cannot_be_bypassed_by_forwarded_for | Tras nginx se comparte IP: configurar proxy confiable explícitamente antes de producción |
| Registro automatizado | CAPTCHA imagen local, expirable y un solo intento | test_register_requires_captcha_and_challenge_is_single_use | No evita granjas de resolución; Angular actual no presenta el reto |
| Login automatizado | CAPTCHA desde 3 fallos por IP en 10 min | test_login_demands_captcha_after_three_failures | Acumulación Axes es conservadora dentro de su ventana de 15 min |
| Abuso endpoints caros | login5/min, register3/min, sync2/h, recalcular2/h, export10/min, mfa5/min | tests auth + suite | DRF cache local no es cuota global entre workers; usar cache compartida en producción |
| Repetición de operaciones | Idempotency-Key opcional, usuario+endpoint, hash cuerpo, TTL5 min, DB/lock usuario | test_idempotency_isolated_by_user_endpoint_and_body | Limpieza periódica de filas expiradas pendiente; escritura concurrente soportada en PG |
| Refresh robado/cambio clave | Blacklist refresh + CHECK_REVOKE_TOKEN; mínimo12 caracteres | test_password_change_revokes_refresh_and_access | Password_change invalida sesión actual; gestionar re-login |

Los primeros cinco fallos de credenciales son 401, el sexto 429 account_locked
con Retry-After 900. Un sexto login válido también se limita, code=throttled.
LOGIN_FALLIDO/LOGIN_BLOQUEADO incluyen email intentado e IP, nunca contraseña.
Datos personales en auditoría: acceso ADMIN, retención y borrado bajo procedimiento
de evidencias; no indexar email/IP como labels de alta cardinalidad en Loki.

CAPTCHA_ENFORCED por defecto = not DEBUG; API_DOCS_ENABLED por defecto = DEBUG.
CI conserva las pruebas anteriores con ambos valores explícitos de demo, y prueba
el modo estricto por separado. .env.example muestra configuración local, **no es
plantilla de producción sin revisar**. En producción establecer CAPTCHA_ENFORCED=True,
API_DOCS_ENABLED=False y SECURE_SSL_REDIRECT=True.

## 2. Auditoría encadenada (U3)

| Amenaza | Medida | Prueba | Límite |
|---|---|---|---|
| Cambio de filas | SHA256 canónico v1 + HMAC independiente | test_tampering_detected_or_blocked | Un administrador con DB y clave puede recalcular toda la cadena |
| Bifurcación concurrente | Singleton AuditHead bloqueado en transacción; cabeza compara cola | rollback + PostgreSQL suite | Serializa appends; medir throughput antes de escalar |
| UPDATE/DELETE directo | REVOKE + trigger PostgreSQL SQLSTATE42501 | test_tampering_detected_or_blocked | Propietario/superusuario puede desactivar trigger; separar rol migrador/aplicación |
| Filas históricas | Backfill por PK sin perder detalle/fecha | test_backfill_preserves_and_seals_legacy_row | El backfill acredita el estado en la migración, no autenticidad histórica previa |
| Clave ausente | Arranque prod falla sin AUDIT_HMAC_KEY | test_production_requires_audit_hmac_key | DEBUG deriva clave de SECRET_KEY solo para demo |

`uv run python backend/manage.py verificar_auditoria`: JSON con ok, broken_id,
checked y cause; exit 0/1 y evento equivalente al logger. SHA incluye PK, usuario,
acción, entidad, detalle, IP y fecha ISO UTC; JSON ordenado sin espacios. PK ya es
índice y hash_actual tiene índice único. `audit()` y `log_actividad()` delegan en
registrar(); no editar por ORM/admin. Correcciones: nueva fila accion=CORRECCION,
entidad_id de la original y motivo; preservar la original.

Ante ruptura: detener escrituras, preservar dump/logs/claves por canal separado,
verificar hash externo previamente anclado, seguir [FORENSE](FORENSE.md) y [IR](IR.md).
**No reparar recalculando hashes sobre filas sospechosas**. AUDIT_HMAC_KEY no se
rota como SECRET_KEY: requiere procedimiento de versión de firma y reseal
autorizado con evidencia antigua; TODO rotación HMAC versionada en producción.

## 3. Cabeceras y exposición (U2)

HSTS un año/subdominios/preload si DEBUG=False; cookies Secure/HttpOnly/Strict;
nosniff, referrer strict-origin-when-cross-origin y DENY. Permissions-Policy
desactiva geolocalización/cámara/micrófono. COOP/CORP same-origin y no-store en
auth, incluidos errores. Tests verifican respuestas HTTP reales del test client.

django-csp aplica default/script/connect self; imágenes self/data; object none;
frame-ancestors none. CSS inline permitido por admin/Swagger; **no scripts inline**:
SwaggerSplitView + sidecar local. Producción deshabilita UI, mantiene schema JSON.
Recolectar estáticos con `collectstatic`; el proxy debe servir STATIC_ROOT para
admin/docs si se habilitan. No se integra WhiteNoise ni un CDN nuevo.

TRUST_PROXY_SSL_HEADER=False por defecto. Activarlo solo si backend no es público
y proxy limpia y fija X-Forwarded-Proto; Docker healthcheck conserva su confianza
loopback de Gunicorn. HSTS/preload requiere control de todos los subdominios.

## 4. Operación y respuesta (U2/U3)

[BCP](BCP.md), [IR](IR.md), [FORENSE](FORENSE.md), [RESTORE](RESTORE.md) especifican
responsables funcionales, custodia, restauración y objetivos. Ensayos locales no
son un SLA: TODO asignar personas, aprobar RTO/RPO y ensayar con volumen real.

## 5. SIEM (U1)

[SIEM](SIEM.md): Loki/Grafana/Alloy, cuatro paneles y cinco reglas provisionadas.
Promtail se reemplaza porque terminó soporte el 2026-03-02, según
[Grafana](https://grafana.com/docs/loki/latest/send-data/promtail/).
No se monta el socket Docker; logs se exportan a archivos ignorados. Una alerta
no ejecuta contención automática. TODO contactos/on-call y destino externo de
notificaciones antes de producción; logs Postgres locales pueden ser texto, no
se atribuyen campos JSON que no contienen.

## 6. MFA ADMIN (U1)

Enroll ADMIN genera secreto cifrado/otpauth/QR; verify TOTP habilita y muestra diez
códigos de recuperación **una sola vez**. Login devuelve mfa_required/mfa_token
(cinco minutos, ligado a contraseña y época); verify-login valida TOTP/recovery
y emite tokens. Reto, TOTP y recovery no se reutilizan. Recovery se guarda como
hash aleatorio de 128 bits dentro de Fernet. Disable requiere TOTP, no recovery.

Enrolar/deshabilitar incrementa mfa_epoch y anula accesos anteriores; enrolar
blacklistea refresh existentes. Nunca hay refresh emitido antes de completar el
factor. Seed no enrola ADMIN. Tests en test_mfa.py cubren flujo, replay, scopes,
permisos y sesiones previas. Limitación: MFA opcional para cuentas ADMIN; Angular
no implementa el segundo paso y no podrá ingresar con una cuenta enrolada.
MFA_ENROLL/MFA_VERIFY_OK/MFA_VERIFY_FAIL/MFA_DISABLE no incluyen códigos/secreto.

## 7. Cifrado (U2)

Fernet (`cryptography`) protege mfa_secret_enc/recovery_codes_enc. Claves de
proveedor existentes están en entorno, no en tablas; no se agregan campos de
tokens ficticios. FIELD_ENCRYPTION_KEY y MFA_KEY obligatorias en producción,
Fernet validada al arranque. DEBUG deriva claves solo para compatibilidad local.

Rotación: parar escritores, hacer backup y preservar la clave antigua separada;
inyectar FIELD_ENCRYPTION_KEY_OLD y FIELD_ENCRYPTION_KEY_NEW por gestor de secretos;
`uv run python backend/manage.py rotar_field_key`; cambiar FIELD_ENCRYPTION_KEY a
NEW, reiniciar, verificar MFA y borrar OLD del entorno operativo. La transacción
recifra todos los campos o revierte; no pasar claves por argumentos/terminal
registrado. Test roundtrip/rotación local; TODO ensayo de rotación real/offline y
gestión de backups cifrados con claves antiguas.

## 8. Backups (U3)

[RESTORE](RESTORE.md): scripts backup.sh/restore.sh, pg_dump custom, GPG AES256,
timestamp UTC, SHA256 y destino local o S3. Restore confirma explícitamente la
base objetivo y verifica hash antes de descifrar/destruir. No se instala AWS CLI
en runtime; opción bucket exige CLI y credenciales externas. TODO programación
semanal y ensayo S3: no hay bucket/secretos autorizados. Restauración local se
mide sobre PostgreSQL efímero; seed siempre opcional, nunca en recuperación real.

## 9. Integración (U2)

[INTEGRACION_SEGURIDAD](INTEGRACION_SEGURIDAD.md) y
[SEGURIDAD_FRONTEND](SEGURIDAD_FRONTEND.md). No cambia el código Angular.
La demo DEBUG mantiene login/registro anterior; producción exige cliente con
CAPTCHA y ADMIN enrolado requiere MFA. **No declarar la interfaz lista para esos
flujos hasta implementarlos**. TLS real/CORS entre dominios se verifica por
despliegue, no se acredita con localhost HTTP.

## Evidencias

Resultados reproducibles y archivos por etapa en [VALIDACION_SEGURIDAD](VALIDACION_SEGURIDAD.md).
Ver también [SECURITY.md](../SECURITY.md) para divulgación. Criterios de CI remoto
pendientes de push/ejecución: no se declara una ejecución GitHub no realizada.
