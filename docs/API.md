# Contrato API

OpenAPI se genera desde serializers y decoradores: `GET /api/schema/` (YAML/JSON por negociación), Swagger `GET /api/docs/`. Validar con `python backend/manage.py spectacular --validate --fail-on-warn --file docs/openapi.yaml`.

Autenticación: `Authorization: Bearer <access>`. Health, registro, login, refresh y documentación públicos. El resto requiere usuario activo. Códigos principales: 400 datos inválidos, 401 sin sesión/token vencido, 403 permisos, 404 invisible/inexistente, 409 versión antigua/conflicto, 429 límite. Errores tienen envoltura única en español.

Listados: `{count,next,previous,results}`, `page`, `page_size` (20 por defecto, máximo 500), `ordering` para campos permitidos y prefijo `-` descendente. Países/portafolios tienen `search`. Seguir `next` hasta null al cargar históricos completos. Tendencias genera hasta 15 puntos (3 países × 5 años), incluyendo nulls por ausencia.

| Método | Ruta | Observaciones |
|---|---|---|
| POST | `/api/auth/register/` | email, nombre_completo, password; ANALISTA inicial; rechaza campos de privilegios |
| POST | `/api/auth/login/` | email + password; access/refresh |
| POST | `/api/auth/refresh/` | refresh |
| GET, PUT | `/api/auth/me/` | perfil propio; rol/activo read-only |
| GET | `/api/paises/` | region, search, ordering nombre/codigo_iso/poblacion |
| GET | `/api/paises/{codigo_iso}/` | datos e indicadores |
| GET | `/api/paises/{codigo_iso}/indicadores/` | tipo, anio, ordering anio/tipo/valor |
| GET | `/api/paises/{codigo_iso}/tipo-cambio/` | fecha_desde, fecha_hasta (YYYY-MM-DD); ordering fecha/tasa |
| POST | `/api/paises/sync-indicadores/` | ADMIN; resultado parcial por país y recálculo encadenado; respuesta síncrona |
| GET, POST | `/api/portafolios/` | propios+públicos; ADMIN ve todos; search y es_publico |
| GET, PUT, DELETE | `/api/portafolios/{id}/` | detalle con posiciones/métricas; PUT/DELETE requieren version |
| POST | `/api/portafolios/{id}/posiciones/` | posición + version del portafolio |
| PUT, DELETE | `/api/portafolios/{id}/posiciones/{posicion_id}/` | PUT posición + version; DELETE solo version, conserva histórico |
| GET | `/api/portafolios/{id}/resumen/` | distribución activa, cobertura y riesgo ponderado |
| GET | `/api/portafolios/{id}/export/pdf/` | application/pdf, attachment |
| GET | `/api/riesgo/` | último por país, orden IRPC descendente; nivel_riesgo, ordering |
| GET | `/api/riesgo/{codigo_iso}/` | cálculo, fuentes, faltantes y últimos 20 históricos + URL de histórico completo |
| GET | `/api/riesgo/{codigo_iso}/historico/` | fecha_desde, fecha_hasta, nivel_riesgo; paginado |
| POST | `/api/riesgo/calcular/` | ADMIN |
| GET | `/api/alertas/` | tipo/tipo_alerta, severidad, leida=true/false |
| PUT | `/api/alertas/{id}/leer/` | lectura individual del usuario |
| PUT | `/api/alertas/leer-todas/` | todas las visibles no leídas; no depende de paginación |
| GET | `/api/alertas/resumen/` | total/no_leidas/por_tipo/por_severidad |
| GET | `/api/dashboard/resumen/` | cuatro KPIs y cobertura de datos |
| GET | `/api/dashboard/mapa/` | coordenadas, score, nivel/color y parcial |
| GET | `/api/dashboard/tendencias/` | tipo, paises=CO,BR,MX; últimos cinco años cerrados UTC |

Extensiones: GET `/api/health/` devuelve `{}`; GET `/api/portafolios/nombre-disponible/?nombre=...&excluir_id=...` sirve para validación async exacta por dueño. El borrado lógico no libera el nombre.

Auditoría: GET `/api/auditoria/` es una extensión de solo lectura para ADMIN. Listado paginado, filtros `accion`, `entidad_afectada`, `usuario` y ordering `fecha`/`accion`. Los eventos de comandos sin sesión tienen `usuario: null`; los interactivos conservan el identificador del usuario.

Crear portafolio:

```json
{"nombre":"Latam propio","descripcion":"Simulación","es_publico":false}
```

Agregar posición, usando la versión obtenida de GET del portafolio:

```json
{"pais":"CO","tipo_activo":"RENTA_FIJA","monto_inversion_usd":"10000.00","fecha_entrada":"2026-11-16","notas":"Simulación","version":1}
```

La fecha es solo ejemplo; usar una fecha UTC no futura. Montos/tasas/scores son strings decimales. Crear posición incrementa versión; recuperarla en GET detalle/resumen antes de otra escritura. DELETE de posición cierra en fecha UTC actual y devuelve 400 si la entrada es hoy. DELETE de portafolio recibe `{"version":2}` y devuelve 204.

409:

```json
{"error":{"code":"conflict","message":"El registro cambió. Actualiza los datos antes de reintentar.","details":{"detail":"El registro cambió. Actualiza los datos antes de reintentar."}}}
```

Política de visibilidad: un público ajeno es consultable/exportable, no editable. No permitir que el frontend interprete público como colaborativo. Una subida del IRPC significa menor riesgo; `variacion` compara contra el cálculo anterior y `tendencia` es SUBE/BAJA/ESTABLE/SIN_HISTORICO.
