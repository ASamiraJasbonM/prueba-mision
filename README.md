# DataPulse Latam — backend y frontend Angular

Implementación por etapas de Django + DRF con frontend Angular. Backend desplegado en Render Free y frontend en Cloudflare Pages.

## URLs públicas

- Frontend: https://datapulse-latam.pages.dev
- Backend API: https://datapulse-backend-vkc5.onrender.com/api/
- Health check: https://datapulse-backend-vkc5.onrender.com/api/health/

Rama de despliegue: `main`. Configuración y comandos: [guía de despliegue](DEPLOYMENT.md).
Frontend CI compila con `npm run build:pages`, que configura API y CSP. Su job final
publica en Pages el artefacto validado, tras Karma y Docker/Trivy; los despliegues
automáticos de Cloudflare deben estar desactivados. Backend CI contiene su propio
job final para Render, condicionado a todas sus pruebas y controles de seguridad.
Render ejecuta migraciones antes de Gunicorn. Ambos jobs verifican el commit activo;
no hay un workflow de despliegue separado.

En Render, `CORS_ALLOWED_ORIGINS=https://datapulse-latam.pages.dev` y
`ALLOWED_HOSTS=datapulse-backend-vkc5.onrender.com`. Las claves y la conexión
PostgreSQL se guardan fuera de Git; las cuentas desplegadas tienen contraseñas
aleatorias y no usan la contraseña pública del seed local.

Verificación del 19 de noviembre de 2026: salud HTTP 200, preflight CORS desde
Pages, login de analista, consulta autenticada de 10 países, CAPTCHA PNG y
fallback de una ruta interna Angular. Los datos iniciales son DEMO sintéticos.

## Desarrollo local (PowerShell, Python 3.12 y uv 0.10.11)

```powershell
uv sync --frozen
Copy-Item .env.example .env
# Sustituir SECRET_KEY en .env por un secreto aleatorio local.
uv run --frozen python backend/manage.py check
uv run --frozen python backend/manage.py migrate
uv run --frozen python backend/manage.py seed_data
uv run --frozen python backend/manage.py runserver 127.0.0.1:8000
```

La configuración lee `.env` desde la raíz. `SECRET_KEY` es obligatorio. SQLite local; PostgreSQL mediante `DATABASE_URL`. `DEBUG=False` activa cookies seguras y redirección HTTPS salvo ajuste explícito para un proxy de desarrollo.

uv crea y mantiene `.venv`; no se instala el proyecto con pip. `pyproject.toml` declara las dependencias directas y las restricciones transitivas verificadas; `uv.lock` fija resolución, fuentes y hashes. Python queda acotado a `>=3.12,<3.13` para conservar el entorno validado. Las pruebas actuales no requieren paquetes adicionales: el grupo `dev` está vacío. Ver [gestión de dependencias con uv](docs/DEPENDENCIAS_UV.md).

API local: http://127.0.0.1:8000/api/ ; Swagger local: http://127.0.0.1:8000/api/docs/ . Frontend local: http://127.0.0.1:4200 (Angular) o http://127.0.0.1:8080 (Docker). La documentación API está desactivada en el despliegue público.

Documentación: [contrato y payloads](docs/API.md), [arquitectura y ER](docs/ARQUITECTURA.md), [fuentes verificadas](docs/FUENTES.md), [resultados por etapa](docs/ETAPAS.md).

Las adaptaciones de modelo, campos de transparencia y endpoints adicionales están identificados en [Extensiones respecto al PDF](docs/API.md#extensiones-respecto-al-pdf). El resto de operaciones del contrato backend requerido se conserva; las limitaciones de validación y el alcance de la entrega se indican por separado. Los campos de título, mensaje, severidad y tipo de alerta ya pertenecen al modelo del enunciado.

## Estado

Evidencia por etapa en `docs/ETAPAS.md`. El prompt backend del usuario tiene prioridad sobre decisiones recomendadas de `PLAN_CORREGIDO.md`.

La revisión posterior está en [Cierre de observaciones P1–P9](docs/CIERRE_OBSERVACIONES.md), con commits, decisiones y [salida completa de los cinco comandos finales](docs/observaciones/P9.md). Los resultados históricos 0–10 se conservan como evidencia de la evolución; el contrato vigente incluye las correcciones posteriores.

Alcance de este encargo: backend completo y frontend Angular (ver `frontend/README.md`). El PDF asigna 35% a la parte técnica de frontend y 10% al video dentro de los entregables (son esquemas de ponderación distintos). La implementación abarca la parte técnica backend descrita como 40% y los componentes de backend del bloque de integración/tareas descrito como 25%; no se afirma haber obtenido esos puntajes ni cumplir el 100% del PDF. El despliegue público sigue pendiente: `compose.yaml` prepara PostgreSQL local y frontend Docker, pero no proporciona URL pública, HTTPS ni video. La validación real en PostgreSQL está documentada abajo (61 pruebas, sin skips); la validación contra proveedores se declara pendiente.

> Render Free suspende el servicio web por inactividad y el primer acceso puede tardar. La base PostgreSQL gratuita `datapulse-db` expira el 18 de diciembre de 2026, según el panel de Render; conservar un backup externo. El proyecto también puede levantarse en local con `docker compose up`.

## Base de datos y precisión

PostgreSQL es el motor de referencia para precisión decimal y concurrencia. SQLite solo sirve para demostración local: su afinidad NUMERIC puede perder precisión en valores grandes y `select_for_update()` no bloquea filas. Los campos y toda la lógica de negocio usan Decimal; las garantías de PostgreSQL deben verificarse contra ese motor antes de desplegar. Las pruebas locales no equivalen a una validación de concurrencia real en PostgreSQL.

| Campo | max_digits / decimal_places | Uso |
|---|---|---|
| monto_inversion_usd | 12 / 2 | USD 1.000–10.000.000 |
| valor indicador | 28 / 6 | Unidad del proveedor declarada en el registro |
| tasa | 24 / 12 | USD por unidad de moneda local; precisión adicional para COP/PYG |
| variacion_porcentual | 18 / 4 | Porcentaje frente al día UTC anterior exacto; null si falta |
| scores e IRPC | 5 / 2 | Rango 0–100 |
| coordenadas | 9 / 6 | Grados |

Toda normalización usa Decimal y ROUND_HALF_UP. World Bank PIB y PIB per cápita se guardan en USD, sin escalar al persistir; los otros cuatro indicadores en PORCENTAJE. `usd_miles_millones_a_usd` multiplica por 10**9 para cálculos internos. `moneda_local_a_usd` usa exclusivamente un objeto TipoCambio almacenado con destino USD. Los JSON exponen decimales como strings.

## Decisiones IRPC y fechas

- UTC en configuración, timestamps conscientes con `timezone.now()`, fechas de negocio DateField. La tasa se fecha según timestamp UTC del proveedor; no se atribuye una tasa vieja al día actual.
- La variación compara únicamente fecha UTC anterior exacta. La depreciación es `(tasa_inicial / tasa_final - 1) * 100`, con tasa local → USD. Volatilidad: desviación poblacional Decimal de variaciones (hasta 30); con menos de dos observaciones se omite esa penalización.
- Se usan últimos indicadores disponibles; crecimiento PIB requiere año previo consecutivo y valor anterior positivo. Se homogeneiza su unidad en memoria, sin alterar persistencia.
- Datos ausentes omiten la penalización correspondiente, mantienen pesos y marcan `detalle_calculo.parcial/faltantes`. Esto puede sobreestimar el score y nunca debe ocultarse en UI.
- `contar_indicadores_en_riesgo` cuenta una vez cada factor con penalización efectiva mayor que cero según el pseudocódigo. Los seis factores son: PIB per cápita <12.000 USD, inflación >5%, desempleo >7%, deuda/PIB >50%, balanza comercial <0% y crecimiento PIB <1%. Un valor ausente no cuenta. Se elige este criterio porque reutiliza los umbrales explícitos del PDF; contar solo factores severos requeriría inventar otro umbral no definido.
- `detalle_calculo.factores_en_riesgo` guarda la lista de nombres, valores y penalizaciones efectivas; también se guardan el conteo y la penalización por concentración. `penalizaciones` mantiene el desglose completo, incluidos ceros.
- El IRPC se calcula en Decimal sin redondeo intermedio. El valor final se cuantiza a 2 decimales ROUND_HALF_UP y se clasifica contra los umbrales 75/50/25 sobre el valor cuantizado.
- Así se evita mostrar 74.999 como 75.00 en UI mientras la API lo etiqueta MODERADO. La tabla del PDF se interpreta sobre el valor ya presentado al usuario. Los umbrales de penalización de cada indicador se evalúan con su dato de entrada, sin redondearlo para decidir la penalización.
- Alertas cambiarias usan magnitud absoluta >3%; IRPC crítico al primer cálculo crítico o cruce hacia <25, caída >15 frente al anterior; inflación >50 por país/año/valor, INFO por lote de datos cambiados. Claves naturales de evento deduplican reintentos. Lecturas globales son por usuario.
- El hash de entradas y fecha UTC evita duplicar recálculos idénticos del mismo día; una fecha nueva conserva histórico diario. Los metadatos de procedencia forman parte del detalle.

| Escenario | Inflación | Negativos | Score econ. | Score estab. | IRPC | Nivel |
|---|---|---|---|---|---|---|
| PDF (ejemplo del documento) | −25 | 3 | 45 | 80 | 69 | MODERADO |
| Pseudocódigo + 3 negativos | −10 | 3 | 60 | 80 | 75 | BAJO |
| Pseudocódigo + regla propia (5 negativos) | −10 | 5 | 60 | 70 | 72 | MODERADO |

La implementación usa la tercera fila. Las tres filas están cubiertas por pruebas para dejar trazabilidad frente a la discrepancia del PDF (p. 9). En las dos primeras se verifica la composición a partir de sus scores históricos; no son políticas alternativas habilitadas en producción. La tercera se comprueba también desde los indicadores de entrada.

> Nota formal: el PDF contiene una contradicción entre su pseudocódigo y su ejemplo numérico. La implementación sigue estrictamente el pseudocódigo. Para los datos del ejemplo, el pseudocódigo arroja 72 (Riesgo Moderado) en lugar de 69, debido a los umbrales de inflación y al conteo de factores negativos.

Con crecimiento de −3% se cuentan seis factores: estabilidad pasa de 70 a 35 por −30 de recesión y −5 adicionales de concentración. El efecto compuesto es −10,50 (peso 30%), de 72 a 61,50; el conteo adicional por sí solo resta 5 puntos de estabilidad, equivalentes a 1,50 de IRPC. No se altera la fórmula para interpretar «5 puntos adicionales» como una caída total del IRPC. Con los seis indicadores sanos el conteo es cero.

## Portafolios y concurrencia

Público significa visible para otros, editable solo por dueño ANALISTA o ADMIN. VIEWER consulta/exporta pero no escribe. Todos los cambios bloquean el portafolio con `select_for_update()` en `transaction.atomic()`; también crear posiciones. PUT y POST de posiciones incluyen `version` actual del portafolio en JSON. DELETE de portafolio y de posición exigen la cabecera `If-Match: "N"`, donde N es la versión del portafolio padre; no usan body ni query param. Cada escritura incrementa versión; un valor antiguo devuelve 409 y revierte toda la transacción. GET detalle/resumen devuelve versión y `ETag: "N"`. CORS permite If-Match y expone ETag a Angular. El control de versión se prueba en SQLite y en PostgreSQL (61 pruebas, sin skips). Los bloqueos reales de concurrencia requieren PostgreSQL.

Posiciones activas tienen salida null; el límite de USD 50 millones y la distribución se calculan sobre activas. Editar excluye la posición actual del conteo y total. Borrado de portafolio es lógico y su nombre permanece reservado por usuario. La validación asíncrona usa GET `/api/portafolios/nombre-disponible/?nombre=...&excluir_id=...`.

Decisión propia, no exigida por el PDF: las posiciones cerradas no se reabren ni editan; PUT devuelve 400 con la versión vigente. Cerrar el mismo día de entrada devuelve 400 porque el PDF exige `fecha_salida > fecha_entrada`. DELETE fija la salida UTC y conserva el registro; no hay borrado físico de posiciones cerradas. Para registrar una corrección se crea una nueva posición y se referencia el registro original en sus notas. No se documenta «eliminarla y recrearla» como una operación disponible, porque borraría la trazabilidad y esa ruta no existe. Una versión obsoleta sigue devolviendo 409 antes de validar la edición.

El riesgo ponderado usa solo montos con IRPC disponible y devuelve el monto cubierto y países con datos ausentes/parciales. No se reemplaza un riesgo ausente por cero. El PDF tabular incluye posiciones activas/cerradas y advertencia de datos incompletos.

## Operaciones, auditoría y tareas

Los comandos son procesos independientes aptos para cron/Task Scheduler; no requieren Celery/Redis. La sincronización bajo demanda por POST ADMIN espera el resultado; no se anuncia como un job asíncrono. La programación se configura fuera de Django, no se instala automáticamente en este equipo.

```powershell
uv run --frozen python backend/manage.py sync_indicadores
uv run --frozen python backend/manage.py sync_tipos_cambio
uv run --frozen python backend/manage.py recalcular_irpc
uv run --frozen python backend/manage.py sync_paises
```

`sync_indicadores` siempre encadena recálculo, incluso ante fallos parciales; cambio diario también recalcula. Reintentos HTTP: máximo dos adicionales, timeout por petición configurable, solo GET y fallos transitorios. Sincronización por país/indicador, transacciones cortas sin llamadas de red dentro. No se eliminan datos anteriores ante errores. Para REST Countries v5 configurar `REST_COUNTRIES_API_KEY` (ver docs/FUENTES.md).

Código de salida: `sync_indicadores` y `sync_tipos_cambio` terminan con código 0 ante éxito total o parcial, y con código 1 ante fallo total (cero actualizaciones y al menos un error), de modo que cron o GitHub Actions puedan detectar un fallo total del proveedor.

Ejemplo cron UTC, ajustando rutas y entorno; ejecutar desde la raíz del proyecto:

```cron
0 2 * * * cd /srv/datapulse && uv run --frozen python backend/manage.py sync_indicadores >> /srv/logs/indicadores.log 2>&1
0 3 * * * cd /srv/datapulse && uv run --frozen python backend/manage.py sync_tipos_cambio >> /srv/logs/cambio.log 2>&1
```

El proceso obtiene configuración de `.env`; en Windows configurar las mismas acciones en Task Scheduler con el Python del venv y argumentos `backend/manage.py ...`. No superponer ejecuciones del mismo comando en el scheduler.

Logs de aplicación JSON por stdout/stderr: evento, nivel, timestamp UTC y metadatos seguros. Middleware registra método, path sin query, usuario, IP de REMOTE_ADDR y duración en ms; no cuerpos, Authorization ni contraseñas. No se confía en X-Forwarded-For del cliente. LogActividad audita CRUD, login y exportación. Errores DRF: `{ "error": { "code": "...", "message": "...", "details": {} } }`; no se exponen errores internos ni datos del proveedor.

Decisión explícita respecto al modelo del PDF: `LogActividad.usuario` admite `null` para auditar comandos de sistema, que no tienen sesión de usuario. No se crea un usuario técnico ficticio; los eventos interactivos conservan el usuario autenticado y los de sistema se identifican por entidad, acción, detalle y fecha UTC. GET `/api/auditoria/`, de solo lectura para ADMIN, serializa esos eventos como `"usuario": null`. No se requiere migración porque el campo ya era nullable.

## Seed y usuarios demo

`seed_data` es offline e idempotente en el mismo día UTC, no sobrescribe registros existentes. Carga 10 países, 6 indicadores × 5 años × 10 países (300), 31 fechas × 10 monedas (310), 2 portafolios con 5 posiciones y los 10 IRPC. Las 31 observaciones permiten 30 variaciones diarias. Una ejecución en otro día añade las fechas nuevas sin borrar histórico.

La identidad de posiciones demo es estable entre días; no se crean nuevas inversiones por cambiar de fecha. Variaciones nuevas siempre usan la tasa del día anterior realmente persistida, aunque el seed conserve tasas previas importadas o editadas.

Regiones, coordenadas y selección de moneda siguen el PDF (PA=PAB, EC=USD). Población, indicadores y tasas son **sintéticos para demostración**: no son cifras financieras reales ni descargas de proveedores. Indicadores usan fuente MANUAL y tasas DEMO_SINTETICO. Sincronizar reemplaza los registros disponibles por sus fuentes reales, conserva el resto y mantiene faltantes explícitos.

| Usuario | Rol | Contraseña demo |
|---|---|---|
| admin@datapulse.com | ADMIN (también superusuario Admin Django) | DataPulse2026! |
| analista@datapulse.com | ANALISTA | DataPulse2026! |
| viewer@datapulse.com | VIEWER | DataPulse2026! |

Son credenciales públicas de prueba exigidas por el enunciado; no son secretos de infraestructura. Seed no restablece contraseñas de usuarios existentes. En un entorno no demo no ejecutar este comando.

## Pruebas y PostgreSQL

```powershell
uv run --frozen python backend/manage.py test
uv run --frozen python backend/manage.py makemigrations --check --dry-run
uv run --frozen python backend/manage.py spectacular --validate --fail-on-warn --file docs/openapi.yaml
uv run --frozen python scripts/check_numeric_policy.py
```

El runner usa base efímera limpia. Tests verifican constraints, auth/roles, conflictos de versión/rollback, posiciones, IRPC y umbrales, parciales, deduplicación/lectura global, fallos de proveedores, comandos, dashboard, PDF y seed. HTTP externo usa respuestas controladas: no necesita red para pruebas. Dos pruebas específicas de precisión grande y escritores simultáneos se omiten en SQLite y se habilitan en PostgreSQL.

Para PostgreSQL local con Docker activo: definir `POSTGRES_PASSWORD` en `.env`, ejecutar `docker compose up -d db` y establecer `DATABASE_URL=postgresql://datapulse:TU_PASSWORD@localhost:5432/datapulse` (escapar caracteres reservados en URL). Ejecutar migrate, seed y toda la suite de nuevo. La cuenta local necesita permiso de crear la base efímera de pruebas; la cuenta creada por el contenedor lo tiene. El volumen conserva datos entre reinicios; no usar `down -v` si se desean conservar.

PostgreSQL validado: 61 pruebas aprobadas, sin skips (evidencia en `frontend/README.md` y docs). No se han ejecutado sincronizaciones reales con claves personales ni instalado un scheduler. Configurar PostgreSQL, la clave REST Countries y cron antes del despliegue, y cumplir la atribución de ExchangeRate-API descrita en docs/FUENTES.md.


- Etapa 00: Bootstrap, health y OpenAPI base

- Etapa 01: Usuario custom con login por email y administrador demo

- Etapa 01: Verificacion efectiva de usuarios desde directorio backend

- Etapa 02: Modelo relacional completo, constraints e indices

- Etapa 03: Politicas DRF, errores uniformes y throttling

- Etapa 04: Autenticacion JWT, perfiles y permisos seguros

- Etapa 05: Paises, indicadores y sincronizacion idempotente con Decimal

- Etapa 06: IRPC Decimal, alertas y lectura individual

- Etapa 07: Portafolios transaccionales, posiciones y exportacion PDF

- Etapa 08: Dashboard con KPIs, mapa y tendencias de cinco anios

- Etapa 09: Logs JSON, auditoria y comandos programables encadenados

- Etapa 10: Seed completo, regresiones, OpenAPI y documentacion final

## Seguridad y operación

[Controles, pruebas y límites](docs/SEGURIDAD.md) · [Resultados por etapa](docs/VALIDACION_SEGURIDAD.md)
· [Divulgación de vulnerabilidades](SECURITY.md) · [Continuidad BCP](docs/BCP.md)
· [Respuesta IR](docs/IR.md) · [Custodia forense](docs/FORENSE.md)
· [Backup y restore](docs/RESTORE.md) · [SIEM local](docs/SIEM.md)
· [Seguridad frontend](docs/SEGURIDAD_FRONTEND.md) · [Integración segura](docs/INTEGRACION_SEGURIDAD.md).

Producción requiere AUDIT_HMAC_KEY, FIELD_ENCRYPTION_KEY (Fernet válida), MFA_KEY y
SECRET_KEY independientes desde gestor de secretos. DEBUG=False, HTTPS y CAPTCHA
activo; docs UI desactivada por defecto. `.env.example` es para demo local.
MFA del ADMIN es opcional y seed no lo habilita. Angular incorpora login/registro
con CAPTCHA y login MFA mediante TOTP o recovery, con logout entre pestañas.
La página de enrolamiento MFA y el TLS real siguen pendientes de despliegue;
ver [validación frontend](docs/VALIDACION_SEGURIDAD_FRONTEND.md).
Dependencias administradas solo con uv; Docker/CI usan uv 0.13.9 corregido.
