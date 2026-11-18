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

Compatibilidad inicial: la dockerización no incluía CAPTCHA/MFA en el cliente.
El endurecimiento descrito en §3–§7 incorpora esos flujos mínimos; el backend
conserva su contrato. U1: correlacionar401/403 sin registrar cuerpos; U3:
preservar logs de nginx/API según FORENSE. Checklist y límites en
[INTEGRACION_SEGURIDAD](INTEGRACION_SEGURIDAD.md) y [SEGURIDAD §9](SEGURIDAD.md#9-integración-u2).

## 0. Baseline de CI y dependencias — U2

Actualización de seguridad Angular20 (2026-11-18). Se conserva el diseño, los
formularios reactivos, los DTO económicos y las 25 pruebas existentes (el prompt
citaba20). U1/U2/U3 son referencias temáticas del encargo: sus PDFs no se adjuntaron;
no se atribuyen páginas ni citas textuales no verificadas.

| Amenaza | Medida | Prueba ejecutable | Límite |
|---|---|---|---|
| CVEs runtime | audit:prod = npm audit --omit=dev --audit-level=high | CI lint-and-check | Base de avisos cambia con el tiempo |
| Dependencias desactualizadas | Dependabot npm semanal /frontend, grupo, máximo5 PRs | dependabot.yml | PRs necesitan revisión; no actualización forzada |
| Tipos permisivos | tsc app/spec y strict/strictTemplates | CI proyectos explícitos | tsc raíz por sí solo no recorre los references |
| Fuga de fuentes | sourceMap:false y gate recursivo sobre dist | check-production.mjs + prueba negativa con .map | No oculta el JS público ni sustituye controles backend |
| Regresión DOM/logs | check-source-security.mjs prohíbe sinks/bypass/eval/logs verbosos | prueba negativa src/view.ts | Regexp conservadora, no SAST completo |

Se mantienen los cuatro jobs existentes para conservar sus nombres de checks;
no se fusionan en lint-and-test. No hay configuración ESLint/angular-eslint:
no se añade un plugin que nadie ejecutaría ni un `ng lint` ficticio. Se usan los
proyectos TS estrictos, pruebas, auditoría y gates de infraestructura. No se añaden
dependencias npm. package.json solo añade audit:prod y postbuild (prepara/verifica
el artefacto de producción). El output real es dist/datapulse/browser, no
dist/frontend/browser. Angular20 application builder usa optimization:true,
namedChunks:false y AOT por defecto; no admite el antiguo buildOptimizer separado.

Audit actual: **0 vulnerabilidades de producción**; tooling completo: **16
moderadas, 0 HIGH/CRITICAL**. La cifra33 del prompt era histórica. La cadena
@angular/cli→pacote/npmcli/sigstore/tuf/minimatch aporta las16 entradas afectadas
(no16 CVEs independientes). npm sugiere CLI16.2.16 como fix: degradar desde20
rompería la plataforma verificada. No se ejecuta audit fix --force. Decisión de
ingeniería: retención temporal solo en tooling, fuera del runtime nginx; tratar
como riesgo residual, no afirmar que es inocuo. Revisar Dependabot semanalmente
y reevaluar antes de 2026-12-18; responsable funcional: mantenimiento frontend.
No hay aceptación formal de riesgo de una organización distinta a este proyecto.

## 1. XSS y representación — U2

| Amenaza | Medida | Prueba | Límite |
|---|---|---|---|
| HTML de API ejecutable | Interpolación/textContent; sin innerHTML, SafePipe ni bypassSecurityTrust | check-source-security + dom-sanitizer.spec | Auditar nuevas librerías y sinks futuros |
| Script/handler/javascript URL | Escape/sanitizador estándar Angular | dom-sanitizer.spec: script, onerror, javascript y b benigno | La prueba de sanitizador no autoriza introducir HTML dinámico |
| Imagen CAPTCHA externa/activa | Origen API exacto, ruta de imagen/hash40, sin credenciales/query/fragmento | auth-page.spec rechaza URL ajena/javascript | No es escáner del contenido de imágenes |

No se instala DOMPurify porque no hay HTML dinámico que renderizar. Angular ya
escapa los mensajes de la API; Leaflet recibe nodos con textContent. bandera_url
existe en DTO pero **no se usa en un img**: no se abre flagcdn ni ningún CDN por
un campo que no se representa. Tampoco hay enlaces target=_blank actuales.
Si se añaden, exigir HTTPS y rel=noopener noreferrer; no usar bypass como sanitizador.

CAPTCHA se descarga con HttpClient como PNG por CORS y se muestra con blob local;
solo origen API, ruta captcha-image/image/hash, MIME image/png y tamaño≤1MiB.
Así funciona con CORP:same-origin del backend también si API y frontend están en
dominios diferentes. Reemplazar/destruir revoca objectURL. El test no lee soluciones
desde el frontend; las pruebas de navegador consultaron únicamente la BD aislada
de ensayo para resolver retos controlados, sin mostrar respuestas ni secretos.

## 2. CSP y cabeceras — U2

CSP por **cabecera nginx** es la autoridad. postbuild añade meta CSP al index
generado para hosting estático; conserva el origen API validado del build y elimina
frame-ancestors de la meta porque los navegadores no la soportan allí. La cabecera
sí contiene frame-ancestors:none y DENY. No se añade una meta al index fuente que
rompa el websocket de desarrollo o bloquee el API_URL distinto del builder.

connect-src = self + origen exacto API_URL (si es absoluto); img-src permanece
self/data/blob, sin CDN innecesario. Scripts self, sin unsafe-inline/unsafe-eval;
estilos self/unsafe-inline por Material/Leaflet/critical CSS. font-src self,
object none, base-uri/form-action self. security-build.test.mjs valida acuerdo
entre CSP generada/meta, origen adicional, CORP y rechazo de source maps.

Se añade CORP:same-origin a las cabeceras ya presentes. HSTS un año/subdominios/
preload se emite solo cuando nginx **termina HTTPS**, mediante map $scheme; el
contenedor local escucha HTTP8080 y no lo anuncia. Si TLS termina en otro proxy,
ese proxy debe emitir HSTS y controlar todos los subdominios antes de preload.
No se confía en X-Forwarded-Proto arbitrario para fingir HTTPS. Las meta tags no
reemplazan HSTS, X-Frame-Options ni frame-ancestors; no se crean fallbacks engañosos.

TODO: endpoint estable de informes CSP, telemetría con política de privacidad y
nonces para estilos coordinados con el hosting. Sin inventar un colector, no se
envían reportes de usuario a terceros. Referencias: [Angular security](https://angular.dev/best-practices/security),
[frame-ancestors y meta](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors).

## 3. Sesión y logout cross-tab — U2/U3

| Amenaza | Medida | Prueba | Límite |
|---|---|---|---|
| JWT exfiltrado por XSS | localStorage explícito y CSP/escape, nunca logs | source gate y auth-security.spec | Un XSS con ejecución aún puede leer JWT |
| Sesión antigua en otra pestaña | storage event, invalidación de generación y navegación login/returnUrl | test de evento + dos pestañas reales | Storage bloqueado deja sesión solo en memoria |
| Respuesta tardía revive sesión | Generación de sesión en login/refresh/MFA | pruebas existentes y nuevas tardías | No es revocación backend por sí misma |
| Fallo temporal destruye sesión | restore503 conserva tokens; permisos esperan me válido | auth-security.spec | Usuario debe reintentar cuando se recupere API |
| Refresh repetido | Un observable compartido, un reintento por401 | pruebas concurrentes y segundo401 | Cache/session no coordina refresh entre procesos backend |

Claves: datapulse.auth.access y datapulse.auth.refresh. datapulse.auth.change
señala que terminó una escritura de ambos valores; no contiene tokens. Se lee
datapulse.session anterior para compatibilidad y se elimina tras guardar una sesión
nueva. El listener se elimina al destruir el servicio; logout remoto no vuelve
a escribir storage, evitando bucles. Cambio de cuenta en otra pestaña invalida
la vista anterior y solicita reentrada; un refresh de la misma cuenta conserva perfil.

logout acepta manual/expired/revoked/role_changed y borra ambos tokens, perfil y
reto pendiente. Shell, interceptor y listener gestionan navegación/returnUrl en
su contexto; logout() de estado sigue siendo utilizable sin Router (pruebas).
No existe endpoint backend logout/audit de motivos: no se inventa ni modifica
LogActividad. Logout manual y una revocación401 pueden limpiar credenciales;
un error de red/503 del perfil no prueba revocación y no las elimina.

JWT se adjunta solo al origen/ruta API. Login/register/refresh/captcha/imagen y
mfa/verify-login son públicos; me, password-change y mfa/enroll/verify/disable
**sí requieren Bearer**. No se excluye auth/* globalmente. Se admite401 genérico
además de token_not_valid: el contrato y CORS actuales no garantizan que el cliente
pueda leer WWW-Authenticate en otro origen. session_requires_mfa se reconoce si
aparece, pero el backend actual emite authentication_failed ante época MFA distinta;
no se cambia ese contrato. Tras un refresh y otro401 se termina sesión, sin bucles.

TODO opcional: cookies HttpOnly con CSRF, SameSite, backend y pruebas coordinadas
en otro cambio. No se implementa idle timeout que borre sesión sin coordinar con
expiración/UX; la autoridad son los tokens y controles del backend.

## 4. CAPTCHA y MFA mínimos funcionales — U1

| Amenaza/problema | Medida | Prueba | Límite |
|---|---|---|---|
| CAPTCHA obligatorio bloquea la UI | Detectar captcha_required/captcha_invalid, obtener reto e imagen y enviar clave/respuesta | auth-page.spec y registro/login reales | CAPTCHA visual no es accesible para todos; falta alternativa accesible del proveedor |
| Reto consumido | Refrescar imagen tras fallo, limpiar respuesta; clic obtiene otra | prueba de flujo CAPTCHA | Expiración/bloqueo siguen bajo autoridad backend |
| MFA confundido con JWT | Unión validada en runtime; reto solo memoria, sin tokens hasta verify-login | auth-security + auth-page + ADMIN real TOTP | Enrolar MFA sigue siendo operación backend, sin página propia |
| Recovery reutilizado o expuesto | Enviar como code, limpiar input tras intento; backend lo consume | prueba componente con recovery | No se muestran ni almacenan recovery codes en esta UI |
| Registro exitoso reenviado | Recordar éxito en memoria antes del login posterior | test CAPTCHA entre registro y login | Al recargar se vuelve a login manual; no reintentar una creación automáticamente |

Flujo: POST login → User/JWT o mfa_required; si reto, mostrar formulario TOTP6
dígitos o recovery hexadecimal32. mfa_token nunca se escribe en storage ni en
input hidden: AuthService lo mantiene en memoria, ligado a generación. POST
mfa/verify-login envía exactamente {mfa_token,code}; no recovery_code adicional.
Tras recibir tokens válidos consulta me antes de conceder permisos. Volver a login
descarta reto pendiente; abandonar componente cancela solicitudes; secretos de
formulario no se imprimen. Password mínimo12 en registro; login conserva política
de entrada previa para no impedir acceso a una cuenta histórica válida.

La prueba real usó base SQLite y claves dummy aisladas, seed y ADMIN enrolado solo
en esa base. Se completaron TOTP, registro con CAPTCHA y login con CAPTCHA tras
tres fallos401. Imagen blob cargada y dashboard sin violaciones CSP. La segunda
pestaña regresó al login sin identidad antigua tras salir en la primera.

TODO opcional: página ADMIN de enrolamiento/deshabilitación con QR y entrega de
recovery codes una sola vez. No se añade una ruta seguridad con permisos ANALISTA:
los endpoints MFA de administración son exclusivamente ADMIN. Tampoco se publica
un endpoint nuevo ni se modifica el seed habitual.

## 5. Errores y datos sin fugas — U1/U2

| Amenaza | Medida | Prueba | Límite |
|---|---|---|---|
| Stack/secretos en pantalla | Nunca aplanar details;500 usa mensaje fijo,400/409 solo mensaje público acotado | security-interceptors.spec | Un mensaje público validación aún puede contener datos del usuario; se escapa como texto |
| Logs de tokens/errores completos | Sin cuerpos, cabeceras ni objeto Error en consola; bootstrap usa texto fijo | source gate + main.ts | No hay colector cliente de errorId; no fingir correlación inexistente |
| Abuso/reintentos | Retry-After segundos o fecha, cuenta atrás y botones deshabilitados | tests contador30s/900s/fecha | Control cliente complementa, no reemplaza cuotas backend |
| Repetir escritura en409 | Preservar reread/fresh/version y exigir decisión del usuario | suite previa + interceptor no retry409 | Usuario debe revisar conflicto; no se decide una inversión automáticamente |

No se registran details ni siquiera en desarrollo: se omite la excepción opcional
del prompt porque no puede garantizarse que un detalle esté libre de credenciales.
401 protegido intenta refresh una vez;401 de login/MFA se queda en el formulario;
403/404/409/429/5xx tienen mensajes acotados y acciones. LoadingInterceptor mantiene
finalize por petición y no altera el contador ante errores. Retry-After no es un
timer de seguridad independiente y refrescar el navegador no evita el bloqueo servidor.
