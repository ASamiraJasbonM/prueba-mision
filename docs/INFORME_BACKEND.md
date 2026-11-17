# Entrega del backend DataPulse Latam

## Decisiones y alcance

Backend Django 5.2/DRF con las operaciones del contrato backend requerido y extensiones documentadas. Implementación secuencial, migraciones generadas por Django, pruebas ejecutadas por etapa y commits locales incrementales en `feat/backend-datapulse`. Alcance acordado: backend completo; frontend Angular, despliegue público y video de 5–8 minutos quedan fuera de este encargo. No se afirma cumplir el 100% del PDF.

El IRPC se calcula en Decimal sin redondeo intermedio. El valor final se cuantiza a 2 decimales ROUND_HALF_UP y se clasifica contra los umbrales 75/50/25 sobre el valor cuantizado. Las decisiones de faltantes, unidades, permisos, fechas, monedas y seed están desarrolladas en [README](../README.md). Arquitectura y ER en [ARQUITECTURA](ARQUITECTURA.md); contrato y ejemplos en [API](API.md). Las evidencias 0–10 conservan el estado histórico; las observaciones P1–P9 documentan los ajustes posteriores al contrato, incluido If-Match en DELETE.

## Evidencia por etapa

Revisión posterior: [Cierre de observaciones P1–P9](CIERRE_OBSERVACIONES.md), con resultados completos y cambios al contrato. La ejecución global final está en [P9](observaciones/P9.md); no sustituye las validaciones pendientes en PostgreSQL y proveedores reales.

Cada enlace de resultados contiene comandos y salida completa, archivos modificados y estado de pruebas. Los enlaces de código contienen archivos clave completos tal como estaban al cerrar cada etapa; el código vigente está en `/backend`.

| Etapa | Resultado y pruebas al cierre | Archivos, comandos y salidas | Código completo clave |
|---|---|---|---|
| 0 | Bootstrap importa; check y health: 1 prueba | [00](etapas/00.md) | [00](etapas/codigo/00.md) |
| 1 | Usuario custom antes de migrar; superusuario demo; 3 pruebas | [01](etapas/01.md), [migraciones](etapas/migraciones-01.md) | [01](etapas/codigo/01.md) |
| 2 | Modelo, checks, índices y migraciones limpias; 7 pruebas | [02](etapas/02.md) | [02](etapas/codigo/02.md) |
| 3 | Errores, auth por defecto, paginación y throttling; 10 pruebas | [03](etapas/03.md) | [03](etapas/codigo/03.md) |
| 4 | JWT, perfil, roles y usuarios inactivos; 15 pruebas | [04](etapas/04.md) | [04](etapas/codigo/04.md) |
| 5 | Países/filtros, tres clientes, sync parcial/idempotente; 20 pruebas | [05](etapas/05.md) | [05](etapas/codigo/05.md) |
| 6 | Scores Decimal, IRPC parcial, alertas y lecturas; 26 pruebas | [06](etapas/06.md) | [06](etapas/codigo/06.md) |
| 7 | CRUD, versiones 409, posiciones, resumen/PDF; 32 pruebas | [07](etapas/07.md) | [07](etapas/codigo/07.md) |
| 8 | KPIs, mapa y tendencias completas con faltantes; 34 pruebas | [08](etapas/08.md) | [08](etapas/codigo/08.md) |
| 9 | Auditoría, requests JSON y comandos encadenados; 37 pruebas | [09](etapas/09.md) | [09](etapas/codigo/09.md) |
| 10 | Seed, regresiones, documentación y aceptación final; resultado exacto en evidencia | [10](etapas/10.md) | [10](etapas/codigo/10.md) |

Desde etapa 3 se exigió `spectacular --validate --fail-on-warn` antes de cada commit; se corrigieron las advertencias encontradas. Etapas 0–1 configuran OpenAPI base y usuario; etapa 2 añade la migración de dominio. Etapas 3–10 no necesitan cambios de esquema adicionales; el cierre ejecuta `makemigrations --check --dry-run`.

## Árbol principal entregado

```text
backend/
  manage.py
  config/                 settings, urls, WSGI
  core/
    models.py, admin.py   modelo e integridad
    api.py                errores, conflicto, paginación
    authentication.py, permissions.py, auth_api.py
    data_api.py, risk_api.py, portfolio_api.py, dashboard_api.py
    audit.py, observability.py
    migrations/           0001_usuario, 0002_dominio_economico
    services/             números, HTTP/sync, IRPC, alertas, portafolios, PDF, tareas
    management/commands/  seed_data, sync_indicadores, sync_tipos_cambio,
                          sync_paises, recalcular_irpc, create_demo_admin
    tests/                pruebas de modelos, auth, API, dominio y aceptación
frontend/README.md        reserva; sin implementación Angular
docs/                     contrato, diagramas, fuentes, OpenAPI, informes y código por etapa
scripts/                  registro de etapas, snapshots y chequeo de política numérica
pyproject.toml, uv.lock    dependencias directas y resolución exacta transitiva
.env.example, .gitignore, compose.yaml, README.md
```

## Pruebas mínimas y revisión

Cada etapa añadió pruebas y se observó su fallo antes de implementar la funcionalidad. La suite final cubre límites de IRPC/decimales, valores ausentes, A→B→A, deduplicación, lectura global por usuario, JWT vencido/inactivo, privilegios, constraints DB/modelo, aislamiento de fallos externos, seed en múltiples días, rollback transaccional, conflicto de versión, posiciones y exportación PDF.

Revisión independiente final: detectó dos fallos P2 en seed entre días (identidad de posición dependiente de fecha y variación sobre tasa regenerada). Ambos se reprodujeron con prueba fallida, se corrigieron y se revisaron nuevamente sin P1/P2 adicionales en esas correcciones.

## Pendientes y límites de la validación

- SQLite es solo demo local. Dos pruebas específicas PostgreSQL se omiten en este motor; no se afirma haber verificado sus bloqueos ni su precisión en esta máquina. `docker info` no encontró motor Docker disponible. `compose.yaml` permite levantar PostgreSQL cuando esté activo.
- Clientes externos probados con respuestas controladas y documentación oficial; no se completó una sincronización real contra los tres proveedores. REST Countries necesita clave personal en variable de entorno. El seed está marcado como sintético.
- Scheduler documentado, no instalado. Endpoint de sync es síncrono; comandos ejecutables como procesos de background por cron/Task Scheduler.
- Fuera de alcance acordado: frontend Angular, despliegue público y video de 5–8 minutos. No son omisiones accidentales del encargo backend. Frontend corresponde al 35% de la división técnica del PDF; video al 10% de la división por entregables, sin sumar ambos esquemas como una única rúbrica. La implementación atiende el bloque backend (40%) y la parte backend de integración/tareas (25%), sin afirmar nota obtenida ni despliegue completo. `compose.yaml` configura PostgreSQL local y no sustituye la entrega pública. No se hizo push ni se enviaron mensajes/correos.
- La exportación tabular se verifica como PDF; no incluye gráficos (extra opcional del PDF original).

## Ejecutar

Seguir [README](../README.md): instalar dependencias, copiar `.env.example` a `.env`, definir secreto, migrar, seed y `runserver`. Swagger local en `/api/docs/`. Los tres usuarios demo usan la contraseña pública de prueba especificada en README.
