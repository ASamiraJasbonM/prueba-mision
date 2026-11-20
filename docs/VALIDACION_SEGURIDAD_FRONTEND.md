# Validación del endurecimiento Angular — 2026-11-18

> Snapshot histórico de esa revisión. Los conteos de pruebas y pendientes se
> refieren al 18 de noviembre. Estado vigente en [ESTADO_ACTUAL](ESTADO_ACTUAL.md);
> la suite de navegador incorporada después se documenta en [E2E](E2E.md).

## Decisiones por etapa

| Etapa | Resultado | Archivos clave |
|---|---|---|
| 0 | Auditoría runtime, tsc estricto, npm Dependabot y gates de fuentes/artefactos; se conservan cuatro jobs | frontend-ci.yml, dependabot.yml, package.json, check-production.mjs, check-source-security.mjs |
| 1 | Sin HTML dinámico/bypass; no dependencia DOMPurify innecesaria; imagen CAPTCHA validada | api-base.service.ts, auth-page.ts, dom-sanitizer.spec.ts |
| 2 | CSP header+meta coherentes; sin maps/eval; CORP y HSTS condicionado a TLS | angular.json, configure-build.mjs, finalize-index.mjs, nginx.conf, security-build.test.mjs |
| 3 | Claves explícitas, generación de sesión, cross-tab sin bucle y sin destruir sesión por503 | auth.service.ts, auth-types.ts, auth-security.spec.ts |
| 4 | CAPTCHA login/registro y MFA TOTP/recovery funcionales; sin persistir reto ni reenviar registro exitoso | auth-page.ts, auth-page.spec.ts, auth-security.spec.ts |
| 5 | No details ni cuerpos en logs;401 con refresh único,429 con countdown | error-parser.ts, jwt/error.interceptor.ts, security-interceptors.spec.ts, main.ts |
| 6 | Rutas escritura con data.roles, perfil me revalidado; export VIEWER preservado | auth.guards.ts, portafolios/routes.ts, role-security.spec.ts |
| 7 | Sin cambio de negocio; rechazo fecha futura, strings monetarios y timestamps UTC | position-security.spec.ts, dom-sanitizer.spec.ts, pruebas Decimal originales |

Ver [SEGURIDAD_FRONTEND](SEGURIDAD_FRONTEND.md) para amenaza→medida→prueba→límite
y referencias U1/U2/U3. No se cambia backend, migraciones, DTO económico, pruebas
existentes, librerías ni runner de pruebas. El prompt decía20 pruebas; había25,
todas se conservan. En total **50 Karma/Jasmine** y **8 Node**.

## Comandos y resultados locales

```text
npm run build
  Build producción correcto; postbuild CSP presente, sin source maps/handlers inline.
npm run test:ci
  TOTAL: 50 SUCCESS (ChromeHeadless)
node --test docker/build-config.test.mjs docker/security-build.test.mjs
  8 pass, 0 fail
npx tsc --noEmit
npx tsc -p tsconfig.app.json --noEmit
npx tsc -p tsconfig.spec.json --noEmit
  Sin errores; CI valida explícitamente app y spec.
npm run audit:prod
  Producción: 0 vulnerabilidades.
node docker/check-source-security.mjs
  Sin HTML bypass, eval/Function o logging verboso en código de aplicación.
node docker/check-production.mjs
  Meta CSP presente y ningún archivo .map en dist/datapulse/browser.
actionlint .github/workflows/frontend-ci.yml
  Sin errores.
```

Tooling audit completo:16 moderadas, sin HIGH/CRITICAL. No se aplica el downgrade
CLI16 que sugiere npm ni audit fix --force. El riesgo residual, responsable funcional
y revisión≤2026-12-18 están en §0. No hay ESLint configurado: no se afirma haberlo
ejecutado. BuildOptimizer no corresponde al builder Angular20 actual.

Las búsquedas de fuente (excluyendo specs con ataques intencionales) no encuentran
innerHTML, bypassSecurityTrust, eval, document.write o console.log. `unsafe-eval`
no aparece en fuente/artefacto. Number() legítimo para gráficos/IDs/Retry-After se
documenta: el código de decisiones monetarias conserva BigInt/string.

## Pruebas con backend real y navegador

Base aislada tmp/frontend-security-integration.sqlite3, servidor127.0.0.1:18011,
nginx frontend producción127.0.0.1:18012, claves dummy y CAPTCHA_ENFORCED=True.
No se cambia `.env` ni el ADMIN de la demo habitual.

- ADMIN aislado enrolado con secreto aleatorio cifrado; contraseña → formulario
  MFA → TOTP → dashboard ADMIN. JWT solo tras verificación y me.
- Registro responde captcha_required, carga PNG blob visible, envía reto y llega
  al dashboard del usuario nuevo. No se escribe ni se muestra la solución en informe.
- Tres fallos de login controlados401; siguiente solicitud Angular presenta
  CAPTCHA y completa el login del ANALISTA al resolverlo.
- Dos pestañas comparten sesión; salir en una elimina ambos JWT y la otra va a
  /login?returnUrl=/dashboard sin identidad ni contenido del ADMIN anterior.
- Todas las etapas anteriores: **0 violaciones CSP**. El formulario de segundo
  factor nunca persiste mfa_token ni recovery/TOTP en storage.

Los ensayos manuales no usan Cypress/Playwright ni añaden paquetes. Para repetir,
crear una BD de ensayo, inyectar claves dummy y seguir el flujo API documentado;
nunca enrolar/deshabilitar una cuenta de producción para probar.

## Código y pendientes

[Código completo de archivos clave](seguridad/CODIGO_FRONTEND.md). Evidencias locales
en tmp/frontend-security-*; datos, logs, soluciones y tokens de ensayo no se versionan.
El output de build es dist/datapulse/browser, que contiene meta CSP como fallback;
frame-ancestors/HSTS requieren hosting HTTP adecuado y no se fingen con meta.

TODO: página opcional de enrolamiento/deshabilitación MFA, CAPTCHA accesible,
nonces de estilos, endpoint de reportes CSP, cookies HttpOnly coordinadas con
backend y verificación de dominio/TLS reales. Los controles cliente no reemplazan
la validación backend de roles, ownership, cuotas, revocación o versión.

El workflow actualizado se valida conservando auditoría y Trivy bloqueantes;
la ejecución remota y su enlace se comunican al finalizar, sin inventar resultados
de GitHub antes de que terminen los jobs.
