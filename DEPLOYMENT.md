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
10. Desactivar Auto-Deploy: GitHub Actions llama al hook después de Backend CI.
11. Settings > Deploy Hook: guardar como secreto Actions `RENDER_DEPLOY_HOOK_URL`
    en GitHub > repositorio > Settings > Secrets and variables > Actions.

Render Free no ofrece Shell ni pre-deploy commands. El comando de arranque aplica
`migrate --noinput` antes de iniciar Gunicorn y falla si las migraciones fallan.
El CMD normal de Docker sigue intacto; el override solo se usa en Render.

El seed se ejecuta **una vez**, desde un entorno local controlado con las cuatro
claves y la URL externa PostgreSQL con TLS (`sslmode=require`):

```sh
uv run --frozen python backend/manage.py migrate --noinput
uv run --frozen python backend/manage.py seed_data
```

`seed_data` crea cuentas de demostración con contraseña conocida. Antes de publicar
el servicio, reemplazar las contraseñas de las tres cuentas por claves aleatorias
independientes o inutilizar sus contraseñas. No ejecutar seed en cada reinicio.
No subir la URL PostgreSQL, hooks ni claves a Git, README o logs de CI.

## Cloudflare Pages

1. Workers & Pages > Create application > Pages > Import an existing Git repository.
2. Seleccionar el repositorio, rama de producción `main`, directorio raíz vacío.
3. Build command: `cd frontend && npm ci --no-audit --no-fund && npm run build:pages`.
4. Build output directory: `frontend/dist/datapulse/browser` (el proyecto se llama datapulse).
5. Variables de build públicas: `NODE_VERSION=22.12.0`, `SKIP_DEPENDENCY_INSTALL=true`,
   `API_URL=https://HOSTNAME-REAL.onrender.com/api/`.
6. Save and Deploy, sin contratar planes ni complementos de pago.

`build:pages` configura environment y CSP con el origen de la API antes del build,
finaliza el HTML sin scripts inline, valida el artefacto y genera `_headers`.
`public/_redirects` conserva las rutas Angular al recargar una página interna.
No introducir secretos del backend en variables de build del frontend.
`SKIP_DEPENDENCY_INSTALL` evita que Pages intente instalar el backend Python de la
raíz; `npm ci` continúa ejecutándose explícitamente en el comando de build.

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
