# Despliegue gratuito: Render + Cloudflare Pages

## Respaldo cifrado y verificación de restauración

`.github/workflows/backup-verification.yml` ejecuta a las 04:00 UTC diariamente
solo en main y con el entorno production-maintenance. Requiere autorización para
extraer la base y la variable de repositorio DATAPULSE_BACKUPS_ENABLED=true. Sin
esa variable, el job no se ejecuta. Usa las claves existentes y un secreto nuevo
DATAPULSE_BACKUP_KEY, independiente de las claves de aplicación; conservar su copia
de recuperación fuera de Git. No se rota al desplegar.

El origen exige PostgreSQL con TLS y se consulta en una transacción READ ONLY con
snapshot exportado: pg_dump y conteos usan la misma instantánea. Solo se conservan
ciphertext Fernet autenticado, SHA256 y un informe seguro durante 14 días como
artifact. No se suben dump plano ni claves. Se utiliza cliente/servidor temporal de
la misma versión mayor que el origen, incluyendo la ruta de datos de PostgreSQL 18.
La restauración solo admite un contenedor nuevo marcado por la herramienta: nunca
una URL de destino productiva. Verifica conteos, esquema y cadena HMAC de auditoría.

Ejecución manual: Actions → Respaldo y verificación de recuperación → Run workflow.
Activar sync_countries únicamente con el secreto DATAPULSE_REST_COUNTRIES_API_KEY
configurado en production-maintenance; primero termina el respaldo y después se
ejecuta el comando real de metadatos. Los errores del proveedor hacen fallar el job
y quedan en country-report.json. Las muestras demo del proveedor se rechazan.

Retención de 14 días no sustituye archivo de largo plazo: descargar y custodiar
copias y clave antes de la caducidad del hosting. Recuperación: [RESTORE](docs/RESTORE.md).

## Render

1. New > Web Service > repositorio `ASamiraJasbonM/prueba-mision`.
2. Rama `main`, runtime Docker, Dockerfile `./Dockerfile`, contexto raíz.
3. Región Virginia (igual que `datapulse-db`), instancia **Free**.
4. Docker Command: `sh scripts/render-start.sh`; Health Check Path: `/api/health/`.
5. Variables secretas: `SECRET_KEY`, `AUDIT_HMAC_KEY`, `MFA_KEY`, `FIELD_ENCRYPTION_KEY`.
   Generación documentada en `.env.example`; conservar las mismas claves en cada redeploy.
6. `DATABASE_URL`: conexión **interna** de `datapulse-db` (Add from Database si aparece).
7. `DEBUG=False`, `CAPTCHA_ENFORCED=True`, `API_DOCS_ENABLED=False`,
   `SECURE_SSL_REDIRECT=True`, `TRUST_PROXY_SSL_HEADER=True`, `PORT=8000`.
8. `ALLOWED_HOSTS`: hostname público exacto de Render, sin esquema ni barra final.
9. `CORS_ALLOWED_ORIGINS`: origen HTTPS exacto de Pages, sin barra final; nunca `*`.
10. Desactivar Auto-Deploy: el job final `deploy-render` de Backend CI llama al hook
    solo después de lint, SQLite, PostgreSQL, build y Trivy satisfactorios.
11. Settings > Deploy Hook: guardar como secreto Actions `RENDER_DEPLOY_HOOK_URL`
    en GitHub > repositorio > Settings > Secrets and variables > Actions.

Render Free no ofrece Shell ni pre-deploy commands. El comando de arranque aplica
`migrate --noinput` antes de iniciar Gunicorn y falla si las migraciones fallan.
Render y el CMD de Docker ejecutan `scripts/serve_backend.py`, supervisor de
Gunicorn y `procesar_sincronizaciones`. Compose aplica migraciones antes del mismo
supervisor. Ambos procesos usan la base configurada y las claves existentes; no se
añaden broker ni secretos. Si uno termina, el supervisor detiene ambos y sale con
error para permitir reinicio por la plataforma. La cola sobrevive en PostgreSQL.
El supervisor fija SYNC_WORKER_REQUIRED=True: readiness exige heartbeat de menos
de 90 segundos. No publicar una versión cuya migración 0008 no haya terminado.
Antes de publicar Pages, su job espera el mismo SHA saludable en Render. Es una
comprobación de lectura, sin invocar el hook ni desplegar de nuevo el backend; evita
publicar la UI de trabajos mientras la API todavía conserva el contrato anterior.
El adaptador WSGI de infraestructura añade `X-Deployment-Commit` únicamente al
healthcheck y readiness, usando `RENDER_GIT_COMMIT` de la plataforma. El job fija
el SHA en el hook y espera HTTP 200 con ese mismo SHA en ambas rutas; una versión
anterior sana o un proceso vivo con base/caché inaccesibles no bastan.
No necesita una clave de API de la cuenta de Render.

La configuración actual de Render conserva `/api/health/` como liveness. El gate
adicional de CI consulta `/api/ready/` y el healthcheck Docker usa esa ruta.
Puede utilizarse como readiness de un balanceador: 200 cuando base y caché responden,
503 con error genérico cuando no. Las dos sondas son públicas, sin autenticación ni
throttling; no devuelven datos de negocio, DSN ni excepciones internas.

## Caché y cuotas compartidas

Con DEBUG=False y sin override, CACHE_SHARED=True activa la caché PostgreSQL en
`datapulse_cache`. Para habilitarla explícitamente, configurar CACHE_SHARED=True en
Render; no se precisa un servicio ni secreto nuevo. Si se copió el .env de desarrollo,
revisar su CACHE_SHARED=False antes de usarlo en producción.

La migración 0007 solo crea la tabla de caché e índice de expiración, sin modificar
usuarios, portafolios, indicadores ni auditoría. El arranque de Render aplica la
migración antes de Gunicorn; readiness comprueba también la lectura de esa tabla.
No ejecutar createcachetable por separado: el esquema pertenece a las migraciones.

Los throttles conservan 100/min autenticados, 20/min anónimos y las cuotas de acción.
En PostgreSQL, cada identidad/scope usa un advisory lock de transacción mientras
lee/guarda su historial compartido. El lock termina antes de ejecutar la vista;
no se mantiene durante llamadas externas ni escrituras de negocio. Una escritura
fallida de cuota se rechaza con 503. La prueba de concurrencia usa cuatro conexiones
independientes y acredita que una sola puede consumir el último slot disponible.

La tabla contiene únicamente estado de caché y expiración. Tiene límite de 10.000
entradas y limpieza por expiración/culling de Django; no es una caché de respuestas
financieras. El cliente sigue identificado por usuario o REMOTE_ADDR: no se amplía
la confianza de X-Forwarded-For. Las cuotas no sustituyen una protección DDoS de borde.

El seed se ejecuta **una vez**, desde un entorno local controlado con las cuatro
claves y la URL externa PostgreSQL con TLS (`sslmode=require`):

```sh
uv run --frozen python backend/manage.py migrate --noinput
uv run --frozen python backend/manage.py seed_data
```

Este despliegue contiene únicamente datos de evaluación. Después del seed ejecutar
una sola vez, con las mismas claves y conexión PostgreSQL externa:

```sh
uv run --frozen python backend/manage.py prepare_evaluation_accounts --confirm-demo
```

Configura exclusivamente `admin@datapulse.com`, `analista@datapulse.com` y
`viewer@datapulse.com`, con roles ADMIN/ANALISTA/VIEWER y `DataPulse2026!` exigida
por el PDF. No cambia portafolios, otras cuentas ni claves de infraestructura.
Las tres cuentas carecen de permisos staff/superuser de Django. No deshabilita MFA:
si alguna ya lo tiene, aborta sin cambios. Repetir el comando no rota contraseñas
ni escribe auditoría si las cuentas ya están configuradas. No usarlo con datos reales.
En un servicio con datos reales se mantienen credenciales privadas independientes.
No ejecutar seed ni este comando automáticamente en cada reinicio.
No subir la URL PostgreSQL, hooks ni claves a Git, README o logs de CI.

## Cloudflare Pages

1. Workers & Pages > Create application > Pages > Import an existing Git repository.
2. Seleccionar el repositorio, rama de producción `main`, directorio raíz vacío.
3. En Settings > Builds > Branch control, desactivar las publicaciones automáticas
   de producción y las de preview. Así ningún push publica en paralelo al CI.
4. Crear un token limitado a la cuenta actual con permiso Account > Cloudflare
   Pages > Edit. Guardarlo como secreto GitHub `CLOUDFLARE_API_TOKEN`, sin imprimirlo.
   El token configurado vence el 19 de diciembre de 2026; renovarlo y actualizar
   ese secreto antes del vencimiento si se conserva el despliegue.
5. Frontend CI usa Node 22.12.0 y `npm run build:pages`, con
   `API_URL=https://datapulse-backend-vkc5.onrender.com/api/`.
6. El job `build` valida y guarda `frontend/dist/datapulse/browser` como artefacto
   `frontend-dist`, incluyendo `deployment.json` con el SHA del commit.
7. `deploy-cloudflare` depende de lint, Karma, build y Docker/Trivy. Descarga el
   artefacto de esa ejecución y lo publica con Wrangler 4.165.0, sin recompilar.
   Después verifica el SHA público, la página Angular y las cabeceras CSP.
8. Los dos jobs de despliegue solo se ejecutan en push/manual de `main`; PR y
   ramas de desarrollo ejecutan controles sin recibir credenciales de despliegue.

`build:pages` configura environment y CSP con el origen de la API antes del build,
finaliza el HTML sin scripts inline, valida el artefacto y genera `_headers`.
El artefacto Pages usa el fallback SPA nativo y no publica la regla `_redirects`
que Cloudflare rechaza por bucle. El archivo solicitado permanece en `public/`;
el build de Pages lo retira del artefacto final, sin introducir un `404.html`.
No introducir secretos del backend en variables de build del frontend.
La configuración de build Git antigua queda inactiva al deshabilitar los builds
automáticos. El sitio sigue en Pages Free y conserva el mismo dominio.

## Operación de los pipelines

- `.github/workflows/backend-ci.yml`: incluye `deploy-render` como último job.
- `.github/workflows/frontend-ci.yml`: incluye `deploy-cloudflare` como último job.
- No existe un workflow de despliegue separado. La concurrencia de `main` evita
  cancelar una publicación ya iniciada; en otras ramas se cancelan ejecuciones
  obsoletas. Ningún despliegue puede continuar si fallan sus dependencias.
- Reintentar desde Actions una ejecución de `main` conserva su SHA y artefacto.
  Revisar la versión activa antes de reintentar una ejecución antigua.

## Tareas diarias reales

La rama predeterminada del repositorio es `main`, que también es la rama desplegada.
`.github/workflows/cron-tasks.yml` corre diariamente a las 02:00 UTC (21:00 del día
anterior en Bogotá) o manualmente sobre `main`. Usa management commands contra
PostgreSQL externo con TLS: no necesita un JWT ni ocupa un worker HTTP de Render.
No aplica migraciones ni ejecuta seed; comprueba primero que el esquema esté vigente.

Configurar estos cinco secretos en el entorno GitHub `production-maintenance`:

| Secreto Actions | Valor de la configuración de Render |
|---|---|
| DATAPULSE_DATABASE_URL | URL **externa** PostgreSQL con `sslmode=require` o superior |
| DATAPULSE_SECRET_KEY | SECRET_KEY |
| DATAPULSE_AUDIT_HMAC_KEY | AUDIT_HMAC_KEY de la cadena existente |
| DATAPULSE_FIELD_ENCRYPTION_KEY | FIELD_ENCRYPTION_KEY |
| DATAPULSE_MFA_KEY | MFA_KEY |

Restringir ese entorno a `main`. No imprimir secretos ni crear nuevas claves HMAC
para esta tarea: deben coincidir con la base existente. Si falta configuración,
el workflow falla. La verificación de auditoría previa evita escribir con una clave
equivocada. La concurrencia impide solapar dos ejecuciones de mantenimiento.

El workflow ejecuta `sync_diaria --task indicadores` y
`sync_diaria --task tipos_cambio` en jobs independientes, con `fail-fast: false`:
una demora o fallo de World Bank no impide el cambio diario. Cada job recalcula
el IRPC y verifica la auditoría. Sin `--task`, el comando intenta ambas operaciones
en secuencia. Conserva los datos anteriores ante fallos de proveedor.
El mantenimiento consulta los países agrupados por indicador (seis peticiones
habituales), según la [estructura oficial de World Bank](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures).
Se conserva el modo por país de la API interactiva y se reutilizan las mismas
validaciones, transacciones y reglas de alertas al persistir cada registro.
Datos sin cambios cuentan como éxito; errores parciales, totales o de recálculo
producen salida distinta de cero y un informe JSON por tarea. El workflow conserva
ese informe como artifact y verifica de nuevo la cadena de auditoría.

Tras configurar secretos, ejecutar Actions → Cron de sincronización programada →
Run workflow, rama `main`, y revisar `maintenance-indicadores` y
`maintenance-tipos_cambio`. Un check verde
sin informe de ambas tareas no constituye evidencia de sincronización.

## Sincronización final

En Render > Environment, establecer literalmente:

```dotenv
CORS_ALLOWED_ORIGINS=https://NOMBRE-REAL.pages.dev
```

Guardar y redesplegar. Si se cambia el dominio público del backend, actualizar
`ALLOWED_HOSTS` y `API_URL` y volver a compilar Pages. Verificar `/api/health/`,
el preflight CORS desde Pages, CAPTCHA/login y una ruta interna recargada.

Las instancias web Free se duermen por inactividad. PostgreSQL Free expira a los
30 días; consultar la fecha exacta de la base en Render y realizar backups fuera
de su filesystem efímero. No son garantías de disponibilidad de un plan de pago.
