# Seguridad del despliegue frontend

Este documento se incorpora con la dockerización: no existía en el estado inicial del repositorio. Define las cabeceras aplicadas por `frontend/nginx.conf` y el generador `frontend/docker/configure-build.mjs`.

## CSP efectiva

```text
default-src 'self';
script-src 'self';
style-src 'self' 'unsafe-inline';
font-src 'self';
img-src 'self' data: blob:;
connect-src 'self' [origen público de API_URL si es absoluto];
object-src 'none';
base-uri 'self';
frame-ancestors 'none';
form-action 'self';
worker-src 'self' blob:
```

La política se envía en todas las respuestas, incluidas rutas SPA, estáticos, errores y el proxy de API. El origen adicional de `connect-src` se calcula con URL y se valida durante el build, sin interpolar texto libre en nginx. No se permite `unsafe-eval` ni scripts inline.

Angular Material, Leaflet y el CSS crítico generado necesitan estilos inline; por ello se permite `unsafe-inline` únicamente en `style-src`. Una evolución a nonces de estilos requiere coordinación con el bootstrap Angular y queda fuera de este cambio de infraestructura.

Angular genera un `onload` inline para activar una hoja de estilos con `media=print`. El paso de infraestructura `finalize-index.mjs` convierte ese enlace del HTML generado en un stylesheet normal y rechaza handlers/scripts inline inesperados. No cambia componentes Angular, `angular.json` ni el `index.html` fuente. Así el CSS carga con `script-src 'self'` sin relajar la política de scripts.

Fuentes, Chart.js, Leaflet y GeoJSON se sirven localmente. El mapa no necesita proveedores externos ni claves. Si se incorporan imágenes o fuentes externas en el futuro, su origen debe revisarse y añadirse explícitamente; no ampliar con `*`.

## Cabeceras y caché

- `X-Content-Type-Options: nosniff`.
- `X-Frame-Options: DENY` y CSP `frame-ancestors 'none'`.
- `Referrer-Policy: strict-origin-when-cross-origin`.
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`.
- `Cross-Origin-Opener-Policy: same-origin`.
- HTML de entrada/rutas SPA: `no-cache, no-store, must-revalidate`.
- Assets con hash: un año e `immutable`; assets sin hash bajo `/assets/`: una semana; favicon: un día.
- Respuestas API y errores: `no-store`. Un asset inexistente devuelve 404; no se convierte en HTML de la SPA.

No se envía HSTS sobre este despliegue HTTP local. El terminador TLS de producción debe configurar HTTPS y HSTS, y coordinar la confianza del proxy con Django/Gunicorn. No se modificó la configuración del backend para asumir cabeceras de proxies arbitrarios.

## Fronteras de configuración

`API_URL` se incorpora al bundle durante el build: es información pública, jamás un lugar para tokens, credenciales ni parámetros secretos. Se rechazan credenciales, query y fragmento. Para otro origen se debe configurar CORS en el backend; el contenedor no lo concede por cuenta propia.

`BACKEND_URL` selecciona solamente el destino del proxy nginx para `/api/`. Se valida como origen HTTP(S) con hostname y puerto opcional antes de envsubst. No acepta rutas, credenciales, espacios ni sintaxis de nginx. El destino HTTPS valida certificado y nombre con las CA del sistema. Authorization, If-Match y cuerpos se reenvían a la API, y ETag/PDF se conservan. El proxy de API no usa la caché de estáticos.

El runtime arranca como nginx (UID 101), puerto 8080, con healthcheck local y sin Node/npm/node_modules. Compose elimina capabilities y activa no-new-privileges. Las bases están fijadas por digest. Durante el build se aplican actualizaciones de seguridad de la misma rama Alpine antes de volver al usuario nginx. Trivy bloquea vulnerabilidades HIGH/CRITICAL, incluidas las que no tengan arreglo: no hay allowlist ni `continue-on-error`.

## Reglas de XSS para mantener

- Mantener el escape de interpolaciones y los bindings seguros de Angular.
- No añadir `bypassSecurityTrust*`, HTML arbitrario, `eval`, `new Function` ni handlers inline.
- Renderizar nombres/mensajes/fuentes de la API como texto. El tooltip del mapa utiliza `textContent`.
- Los tokens actuales viven en localStorage: un XSS podría leerlos. La CSP reduce vías de ejecución, pero no sustituye el escape ni las validaciones del servidor.
- No incluir `.env`, `.npmrc`, claves o credenciales en el contexto ni en las capas de las imágenes.

Referencias: [CSP de Angular](https://angular.dev/best-practices/security#content-security-policy), [cabeceras nginx](https://nginx.org/en/docs/http/ngx_http_headers_module.html), [imagen nginx no privilegiada](https://github.com/nginx/docker-nginx-unprivileged), [caché de Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching).

## Verificación cruzada

U2: CSP connect-src incluye self para proxy /api/ y el origen API validado durante
build si es absoluto. Entre orígenes, CORS_ALLOWED_ORIGINS de Django debe incluir
el origen exacto del frontend; no se necesita CORS para same-origin. Cabeceras
If-Match e Idempotency-Key están admitidas en backend.

La revisión de src confirma que los datos de backend se renderizan mediante
interpolación/textContent; no se usa innerHTML con respuestas API ni se incluyen
SECRET_KEY/credenciales en entornos públicos. No se añaden logs de tokens.
JWT permanece en localStorage y mantiene el riesgo XSS descrito arriba.

Compatibilidad: CAPTCHA y MFA nuevos requieren soporte de cliente no implementado
en esta fase; demo DEBUG conserva flujo previo. Producción no queda acreditada
solo por esas pruebas. U1: correlacionar401/403 sin registrar cuerpos; U3:
preservar logs de nginx/API según FORENSE. Checklist y límites en
[INTEGRACION_SEGURIDAD](INTEGRACION_SEGURIDAD.md) y [SEGURIDAD §9](SEGURIDAD.md#9-integración-u2).
