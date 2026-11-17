# DataPulse Latam — backend

Implementación por etapas de Django + DRF. Frontend reservado; sin despliegue remoto en este encargo.

## Desarrollo local (PowerShell, Python 3.12)

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Sustituir SECRET_KEY en .env por un secreto aleatorio local.
.\.venv\Scripts\python backend/manage.py check
.\.venv\Scripts\python backend/manage.py migrate
.\.venv\Scripts\python backend/manage.py seed_data
.\.venv\Scripts\python backend/manage.py runserver 127.0.0.1:8000
```

La configuración lee `.env` desde la raíz. `SECRET_KEY` es obligatorio. SQLite local; PostgreSQL mediante `DATABASE_URL`. `DEBUG=False` activa cookies seguras y redirección HTTPS salvo ajuste explícito para un proxy de desarrollo.

Si ensurepip falla por permisos del directorio temporal en un sandbox, instalar con el pip anfitrión: `python -m pip --python .venv/Scripts/python.exe install -r requirements.txt`. No reemplazar el intérprete de pruebas por el global.

API local: http://127.0.0.1:8000/api/ ; Swagger: http://127.0.0.1:8000/api/docs/ . No hay URLs públicas: el alcance de este encargo es backend local, sin frontend ni publicación.

Documentación: [contrato y payloads](docs/API.md), [arquitectura y ER](docs/ARQUITECTURA.md), [fuentes verificadas](docs/FUENTES.md), [resultados por etapa](docs/ETAPAS.md).

## Estado

Evidencia por etapa en `docs/ETAPAS.md`. El prompt backend del usuario tiene prioridad sobre decisiones recomendadas de `PLAN_CORREGIDO.md`.

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
- Se cuenta una vez cada uno de los seis factores con penalización: PIB per cápita, inflación, desempleo, deuda/PIB, balanza y crecimiento PIB. El PDF no define esta función.
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

## Portafolios y concurrencia

Público significa visible para otros, editable solo por dueño ANALISTA o ADMIN. VIEWER consulta/exporta pero no escribe. Todos los cambios bloquean el portafolio con `select_for_update()` en `transaction.atomic()`; también crear posiciones. Las peticiones PUT/DELETE y POST de posiciones deben incluir `version` actual del portafolio. Cada escritura incrementa versión; un valor antiguo devuelve 409 y revierte toda la transacción. GET detalle/resumen devuelve la versión nueva. El control de versión se prueba en SQLite; los bloqueos reales requieren PostgreSQL.

Posiciones activas tienen salida null; el límite de USD 50 millones y la distribución se calculan sobre activas. Editar excluye la posición actual del conteo y total. Cerrar conserva el registro y fija la fecha UTC actual; cerrar el mismo día de entrada devuelve 400 porque el PDF exige salida estrictamente posterior. Las posiciones cerradas no se reabren ni editan. Borrado de portafolio es lógico y su nombre permanece reservado por usuario. La validación asíncrona usa GET `/api/portafolios/nombre-disponible/?nombre=...&excluir_id=...`.

El riesgo ponderado usa solo montos con IRPC disponible y devuelve el monto cubierto y países con datos ausentes/parciales. No se reemplaza un riesgo ausente por cero. El PDF tabular incluye posiciones activas/cerradas y advertencia de datos incompletos.

## Operaciones, auditoría y tareas

Los comandos son procesos independientes aptos para cron/Task Scheduler; no requieren Celery/Redis. La sincronización bajo demanda por POST ADMIN espera el resultado; no se anuncia como un job asíncrono. La programación se configura fuera de Django, no se instala automáticamente en este equipo.

```powershell
.\.venv\Scripts\python backend/manage.py sync_indicadores
.\.venv\Scripts\python backend/manage.py sync_tipos_cambio
.\.venv\Scripts\python backend/manage.py recalcular_irpc
.\.venv\Scripts\python backend/manage.py sync_paises
```

`sync_indicadores` siempre encadena recálculo, incluso ante fallos parciales; cambio diario también recalcula. Reintentos HTTP: máximo dos adicionales, timeout por petición configurable, solo GET y fallos transitorios. Sincronización por país/indicador, transacciones cortas sin llamadas de red dentro. No se eliminan datos anteriores ante errores. Para REST Countries v5 configurar `REST_COUNTRIES_API_KEY` (ver docs/FUENTES.md).

Ejemplo cron UTC, ajustando rutas y entorno; ejecutar desde la raíz del proyecto:

```cron
0 2 * * * cd /srv/datapulse && .venv/bin/python backend/manage.py sync_indicadores >> /srv/logs/indicadores.log 2>&1
0 3 * * * cd /srv/datapulse && .venv/bin/python backend/manage.py sync_tipos_cambio >> /srv/logs/cambio.log 2>&1
```

El proceso obtiene configuración de `.env`; en Windows configurar las mismas acciones en Task Scheduler con el Python del venv y argumentos `backend/manage.py ...`. No superponer ejecuciones del mismo comando en el scheduler.

Logs de aplicación JSON por stdout/stderr: evento, nivel, timestamp UTC y metadatos seguros. Middleware registra método, path sin query, usuario, IP de REMOTE_ADDR y duración en ms; no cuerpos, Authorization ni contraseñas. No se confía en X-Forwarded-For del cliente. LogActividad audita CRUD, login y exportación, con usuario null para procesos de sistema. Errores DRF: `{ "error": { "code": "...", "message": "...", "details": {} } }`; no se exponen errores internos ni datos del proveedor.

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
.\.venv\Scripts\python backend/manage.py test
.\.venv\Scripts\python backend/manage.py makemigrations --check --dry-run
.\.venv\Scripts\python backend/manage.py spectacular --validate --fail-on-warn --file docs/openapi.yaml
.\.venv\Scripts\python scripts/check_numeric_policy.py
```

El runner usa base efímera limpia. Tests verifican constraints, auth/roles, conflictos de versión/rollback, posiciones, IRPC y umbrales, parciales, deduplicación/lectura global, fallos de proveedores, comandos, dashboard, PDF y seed. HTTP externo usa respuestas controladas: no necesita red para pruebas. Dos pruebas específicas de precisión grande y escritores simultáneos se omiten en SQLite y se habilitan en PostgreSQL.

Para PostgreSQL local con Docker activo: definir `POSTGRES_PASSWORD` en `.env`, ejecutar `docker compose up -d db` y establecer `DATABASE_URL=postgresql://datapulse:TU_PASSWORD@localhost:5432/datapulse` (escapar caracteres reservados en URL). Ejecutar migrate, seed y toda la suite de nuevo. La cuenta local necesita permiso de crear la base efímera de pruebas; la cuenta creada por el contenedor lo tiene. El volumen conserva datos entre reinicios; no usar `down -v` si se desean conservar.

No se pudo probar ese motor en esta sesión porque Docker no tenía daemon disponible. No se han ejecutado sincronizaciones reales con claves personales ni instalado un scheduler. Configurar PostgreSQL, la clave REST Countries y cron antes del despliegue, y cumplir la atribución de ExchangeRate-API descrita en docs/FUENTES.md.


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
