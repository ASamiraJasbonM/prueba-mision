# Estado vigente de DataPulse Latam

Fecha de revisión: 19 de noviembre de 2026 (America/Bogota). La rama de referencia
y predeterminada es `main`. README, API, ARQUITECTURA, DEPLOYMENT y E2E describen la
entrega actual. Los informes de etapas, observaciones y validaciones fechadas
conservan evidencia del momento en que se ejecutaron: sus límites y conteos no
deben interpretarse como el estado actual del sistema.

| Área | Estado vigente | Evidencia |
|---|---|---|
| Backend | Django/DRF, roles, JWT, datos, IRPC, alertas, portafolios, PDF y auditoría | backend/core y Backend CI |
| Frontend | Angular 20/Material, lazy routes, estado observable, guards, refresh, CAPTCHA y login MFA | frontend/src y Frontend CI |
| UI de país/portafolio | Bandera local con alternativa si falta; pie por país y donut por activo | componentes compartidos y pruebas de navegador |
| Despliegue | Render y Cloudflare Pages por HTTPS, CORS exacto y publicación condicionada a CI | DEPLOYMENT y verificadores de SHA |
| Instalación local | setup_local genera claves independientes y no sobrescribe .env | scripts/setup_local.py y su regresión |
| Acceso demo | Tres roles con DataPulse2026!, sin staff/superuser en las cuentas desplegadas | prepare_evaluation_accounts y verificaciones HTTP |
| Tareas programadas | Dos jobs independientes, secretos restringidos a main, TLS y auditoría | cron-tasks.yml e informes por proveedor |
| Pruebas | Django, Karma/Jasmine, infraestructura Node y Playwright desktop/tablet | workflows y docs/E2E.md |
| Operación | Readiness de base/caché, cuotas compartidas y serializadas en PostgreSQL | health.py, throttling.py, migración 0007 y regresiones de concurrencia |
| Consultas de riesgo | Ranking e históricos con valor anterior calculado en SQL y país precargado | risk_api.py y pruebas de presupuesto de consultas |

## Integraciones reales y duración

El [mantenimiento validado](https://github.com/ASamiraJasbonM/prueba-mision/actions/runs/44669609013)
del commit f53e759 terminó correctamente en ambos jobs. Indicadores procesó diez
países, actualizó 182 registros y terminó sin errores; recálculo: ocho nuevos y
dos existentes. El job completo duró 51 segundos. El de monedas terminó en 40
segundos. Estos tiempos incluyen preparación y verificaciones; no son un SLA.

La API oficial de World Bank puede rechazar consultas agrupadas: se conserva el
fallback por país sin inventar datos ni ocultar fallos finales. Los informes de cada
ejecución distinguen datos actualizados, sin cambios y errores. La actualización
diaria usa procesos externos al servidor HTTP. La acción ADMIN interactiva conserva
su respuesta síncrona; ante proveedores lentos puede superar el timeout del worker.

REST Countries tiene cliente y pruebas controladas, pero aún requiere clave y una
validación real independiente. No se presenta como comprobada. El seed contiene
datos sintéticos etiquetados; las sincronizaciones reemplazan solo los registros
disponibles, conservando trazabilidad y faltantes explícitos.

## Límites que continúan

- localStorage conserva JWT como pide el ejercicio: CSP y escape reducen XSS,
  pero no convierten esos tokens en cookies HttpOnly.
- MFA de ADMIN es opcional y tiene login funcional; falta la pantalla de enrolamiento.
- Caché compartida y locks de cuota están habilitados por defecto con DEBUG=False;
  las garantías concurrentes se validan en PostgreSQL. SQLite/memoria son de desarrollo.
- Liveness conserva su contrato y readiness comprueba base/caché. Ambas rutas publican
  el commit en Render; el pipeline exige que readiness también responda correctamente.
- Reportes PDF tabulares; XLSX, WebSockets y gráficos en el PDF son extensiones opcionales.
- Los planes gratuitos tienen suspensión/caducidad y no equivalen a disponibilidad garantizada.

Los resultados vigentes de pruebas y seguridad se consultan en las ejecuciones
del commit evaluado, no se deducen de conteos antiguos ni garantizan ausencia total
de defectos. Los E2E utilizan exclusivamente una base y claves efímeras locales.
