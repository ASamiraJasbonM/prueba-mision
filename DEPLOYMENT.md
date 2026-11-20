# Despliegue gratuito: Render + Cloudflare Pages

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
El CMD normal de Docker sigue intacto; el override solo se usa en Render.
El adaptador WSGI de infraestructura añade `X-Deployment-Commit` únicamente al
healthcheck, usando `RENDER_GIT_COMMIT` de la plataforma. El job fija el SHA en el
hook y espera HTTP 200 con ese mismo SHA; una versión anterior sana no basta.
No necesita una clave de API de la cuenta de Render.

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

`sync_diaria` intenta indicadores + recálculo y cambio diario + recálculo, incluso
si falla la primera operación. Conserva los datos anteriores ante fallos de proveedor.
Datos sin cambios cuentan como éxito; errores parciales, totales o de recálculo
producen salida distinta de cero y un informe JSON por tarea. El workflow conserva
ese informe como artifact y verifica de nuevo la cadena de auditoría.

Tras configurar secretos, ejecutar Actions → Cron de sincronización programada →
Run workflow, rama `main`, y revisar el artifact `maintenance-report`. Un check verde
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
