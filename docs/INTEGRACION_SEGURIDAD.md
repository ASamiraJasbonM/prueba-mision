# Integración segura (U2; monitoreo U1 y recuperación U3)

```mermaid
flowchart LR
    B[Navegador] -->|HTTPS y CSP| F[Frontend nginx]
    F -->|Red privada o HTTPS verificado / JWT / If-Match| A[Django API]
    B -. API en otro origen / HTTPS / CORS explícito .-> A
    A -->|Rol mínimo / TLS en producción| P[(PostgreSQL)]
    A -->|JSON sin secretos| S[Alloy / Loki / Grafana]
```

## Verificación por despliegue

```sh
curl --fail -I https://<frontend>/
curl --fail --silent --show-error -D - -o /dev/null https://<backend>/api/health/
curl -i -X OPTIONS https://<backend>/api/auth/me/ \
  -H 'Origin: https://<frontend>' -H 'Access-Control-Request-Method: GET' \
  -H 'Access-Control-Request-Headers: authorization,if-match,idempotency-key'
```

- Comprobar CSP connect-src self o el origen exacto de API; no wildcard.
- HSTS en conexión HTTPS backend, DENY/nosniff/Permissions-Policy/no-store auth.
- CORS_ALLOWED_ORIGINS incluye solo origen frontend si hay acceso entre orígenes;
  el proxy same-origin /api/ no requiere CORS en el navegador.
- TRUST_PROXY_SSL_HEADER solo con backend privado y cabecera limpiada por proxy.
- Demo aislada: login con ADMIN/ANALISTA/VIEWER del README; no usar seed en producción.
- Token vencido: refresh válido puede renovar; si refresh vence/revocado, re-login
  preserva returnUrl y no muestra tokens ni trazas. No afirmar que todo401 fuerza
  re-login inmediato: el cliente existente primero intenta refresh.
- 403 por rol y acceso privado404: no mostrar recurso ni datos previos de otra sesión.
- Verificar DELETE conserva If-Match fuerte y POST opcionales Idempotency-Key.

Revisión de fuente: Angular usa interpolaciones/textContent para datos API; no
introduce SECRET_KEY ni imprime tokens en logs. localStorage guarda JWT: XSS puede
leerlo; CSP/escape no lo convierten en HttpOnly. Revisar extensiones y nuevas
dependencias. Ver [SEGURIDAD_FRONTEND](SEGURIDAD_FRONTEND.md#verificación-cruzada).

## Límite de compatibilidad

No se modifica Angular. La demo DEBUG mantiene CAPTCHA desactivado y seed sin MFA.
Producción activa CAPTCHA: el registro y login después de fallos necesitan
captcha_key/captcha_answer; ADMIN enrolado necesita manejar mfa_required y el
segundo POST. **Estos flujos no están implementados en el frontend actual**.
No habilitar un despliegue productivo esperando que esa interfaz los resuelva.
TODO evolución del cliente en otro encargo; no desactivar controles silenciosamente.

Las pruebas backend verifican cabeceras/CORS existentes y permisos; el checklist
HTTPS depende de los dominios/certificados reales, ausentes en este entorno.
[SEGURIDAD §9](SEGURIDAD.md#9-integración-u2), [SIEM](SIEM.md), [RESTORE](RESTORE.md).
