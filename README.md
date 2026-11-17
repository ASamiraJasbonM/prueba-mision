# DataPulse Latam — backend

Implementación por etapas de Django + DRF. Frontend reservado; sin despliegue remoto en este encargo.

## Desarrollo local (PowerShell, Python 3.12)

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Sustituir SECRET_KEY en .env por un secreto aleatorio local.
.\.venv\Scripts\python backend/manage.py check
```

La configuración lee `.env` desde la raíz. `SECRET_KEY` es obligatorio. SQLite local; PostgreSQL mediante `DATABASE_URL`. `DEBUG=False` activa cookies seguras y redirección HTTPS salvo ajuste explícito para un proxy de desarrollo.

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
- Discrepancia PDF: inflación 9,2% penaliza 10 según código, pero 25 según ejemplo. Con los tres negativos asumidos por el ejemplo, el IRPC corregido es 75; con la regla explícita anterior hay cinco negativos, estabilidad 70 e IRPC **72**. Las pruebas usan la fórmula, no el 69 erróneo.
- Umbrales se comparan antes de redondear. Por instrucción transversal del prompt backend, el compuesto se cuantiza a dos decimales HALF_UP **antes de clasificar** (74,995 → 75,00 → BAJO). Esto sustituye la recomendación anterior del plan y la frase contradictoria de etapa 6.
- Alertas cambiarias usan magnitud absoluta >3%; IRPC crítico al primer cálculo crítico o cruce hacia <25, caída >15 frente al anterior; inflación >50 por país/año/valor, INFO por lote de datos cambiados. Claves naturales de evento deduplican reintentos. Lecturas globales son por usuario.
- El hash de entradas y fecha UTC evita duplicar recálculos idénticos del mismo día; una fecha nueva conserva histórico diario. Los metadatos de procedencia forman parte del detalle.

## Portafolios y concurrencia

Público significa visible para otros, editable solo por dueño ANALISTA o ADMIN. VIEWER consulta/exporta pero no escribe. Todos los cambios bloquean el portafolio con `select_for_update()` en `transaction.atomic()`; también crear posiciones. Las peticiones PUT/DELETE y POST de posiciones deben incluir `version` actual del portafolio. Cada escritura incrementa versión; un valor antiguo devuelve 409 y revierte toda la transacción. GET detalle/resumen devuelve la versión nueva. El control de versión se prueba en SQLite; los bloqueos reales requieren PostgreSQL.

Posiciones activas tienen salida null; el límite de USD 50 millones y la distribución se calculan sobre activas. Editar excluye la posición actual del conteo y total. Cerrar conserva el registro y fija la fecha UTC actual; cerrar el mismo día de entrada devuelve 400 porque el PDF exige salida estrictamente posterior. Las posiciones cerradas no se reabren ni editan. Borrado de portafolio es lógico y su nombre permanece reservado por usuario. La validación asíncrona usa GET `/api/portafolios/nombre-disponible/?nombre=...&excluir_id=...`.

El riesgo ponderado usa solo montos con IRPC disponible y devuelve el monto cubierto y países con datos ausentes/parciales. No se reemplaza un riesgo ausente por cero. El PDF tabular incluye posiciones activas/cerradas y advertencia de datos incompletos.


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
