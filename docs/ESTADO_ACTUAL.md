# Estado vigente de DataPulse Latam

Fecha de revisión: 20 de noviembre de 2026 (America/Bogota). La rama de referencia
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
| Seguimiento del mantenimiento | ADMIN consulta último intento, último éxito, códigos de error y cobertura por país; no fabrica historial anterior | MaintenanceRun, migración 0009 y dashboard/mantenimiento |
| Pruebas | Django, Karma/Jasmine, infraestructura Node y Playwright desktop/tablet | workflows y docs/E2E.md |
| Operación | Readiness de base/caché, cuotas compartidas y serializadas en PostgreSQL | health.py, throttling.py, migración 0007 y regresiones de concurrencia |
| Consultas de riesgo | Ranking e históricos con valor anterior calculado en SQL y país precargado | risk_api.py y pruebas de presupuesto de consultas |
| Resumen de portafolio | Dos consultas para posiciones activas y sus últimos riesgos; una si está vacío, sin consultas por país | portfolios.py y test_portfolio_queries.py; incluye desempates, cero y datos parciales |
| Detalles de presentación | Monto agrupa miles automáticamente sin perder centavos; ranking separa País, IRPC, Nivel, Variación y Tendencia | PositionForm, DashboardPage y regresiones unitarias/E2E |
| Validación de nombres | ADMIN consulta nombres del propietario del portafolio editado; exige permiso de escritura | portfolio_api y E2E por propietario |
| Recuperación | Snapshot cifrado de la base demo PostgreSQL 18 restaurado en aislamiento; 33 tablas, esquema y auditoría verificados | RESTORE y backup-verification.yml; clave independiente fuera de Git |

## Integraciones reales y duración

El [mantenimiento validado](https://github.com/ASamiraJasbonM/prueba-mision/actions/runs/44669609013)
del commit f53e759 terminó correctamente en ambos jobs. Indicadores procesó diez
países, actualizó 182 registros y terminó sin errores; recálculo: ocho nuevos y
dos existentes. El job completo duró 51 segundos. El de monedas terminó en 40
segundos. Estos tiempos incluyen preparación y verificaciones; no son un SLA.

La API oficial de World Bank puede rechazar consultas agrupadas: se conserva el
fallback por país sin inventar datos ni ocultar fallos finales. Los informes de cada
ejecución distinguen datos actualizados, sin cambios y errores. La actualización
diaria usa procesos externos al servidor HTTP. La acción ADMIN interactiva devuelve
202 y encola en PostgreSQL; un worker supervisado realiza las llamadas externas,
publica progreso/resultado y recupera trabajos interrumpidos. El dashboard recupera
su ejecución al navegar o recargar. Readiness comprueba también heartbeat del worker.

Dashboard, ranking y país muestran calidad de las entradas del IRPC: procedencia
externa/manual/sintética, antigüedad y ausencias de fecha. Un cálculo con todos los
campos puede seguir requiriendo revisión; su puntuación no se altera. Los MANUAL
antiguos se conservan como no verificados y los nuevos seeds se etiquetan sintéticos.

REST Countries tiene cliente y pruebas controladas. El workflow permite añadir su
job independiente con `incluir_paises=true`, usando el secreto de entorno
DATAPULSE_REST_COUNTRIES_API_KEY. Requiere clave y validación real independiente;
solo una ejecución exitosa acredita esa integración. El seed contiene
datos sintéticos etiquetados; las sincronizaciones reemplazan solo los registros
disponibles, conservando trazabilidad y faltantes explícitos.

El último fallo de mantenimiento auditado (run 44712863509, anterior a esta
revisión) registró 39 ConnectionError de World Bank y cero actualizaciones;
monedas sí pasó. El cron aumenta EXTERNAL_API_TIMEOUT de 5 a 20 segundos: una
sonda individual real tardó 14,4 segundos, mientras la agrupada superó 15. El
fallback y los reintentos se conservan. Esto no garantiza disponibilidad futura;
la ejecución posterior y su informe son la evidencia de recuperación.

La ejecución posterior del commit fa9cd85, [run 44810035993](https://github.com/ASamiraJasbonM/prueba-mision/actions/runs/44810035993),
terminó correctamente en indicadores y monedas. Ambos informes registraron cero
errores, cero actualizaciones y diez IRPC existentes: los datos válidos no habían
cambiado. Acredita consulta real y conservación idempotente, no cobertura externa
total ni disponibilidad futura del proveedor.

CI incorpora cobertura de backend (mínimo 90% de líneas) y frontend (80% de
sentencias, 72% de ramas, 75% de funciones, 85% de líneas). Publica HTML/XML o
HTML/LCOV en artifacts durante siete días. Los reintentos del proveedor respetan
Retry-After con espera máxima de dos segundos y un máximo de dos reintentos,
manteniendo el margen del lease del worker y las regresiones de precisión.

La ventana externa se acumula diariamente. La fuente gratuita no ofrece backfill
histórico; no se compran planes ni se relabelan tasas demo. Calidad muestra fechas
externas únicas /31 y días consecutivos; hacen falta 31 fechas para 30 variaciones.

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
