# Contrato API

OpenAPI se genera desde serializers y decoradores: `GET /api/schema/` (YAML/JSON por negociación), Swagger `GET /api/docs/`. Validar con `python backend/manage.py spectacular --validate --fail-on-warn --file docs/openapi.yaml`.

Autenticación: `Authorization: Bearer <access>`. Liveness, readiness, registro,
login, refresh, CAPTCHA y documentación son públicos. El resto requiere usuario
activo. Códigos principales: 400 datos inválidos, 401 sin sesión/token vencido,
403 permisos, 404 invisible/inexistente, 409 versión antigua/conflicto, 429 límite
y 503 cuando la dependencia operativa/cuota no está disponible. Errores tienen
envoltura única en español.

Listados: `{count,next,previous,results}`, `page`, `page_size` (20 por defecto, máximo 500), `ordering` para campos permitidos y prefijo `-` descendente. Países/portafolios tienen `search`. Seguir `next` hasta null al cargar históricos completos. Tendencias genera hasta 15 puntos (3 países × 5 años), incluyendo nulls por ausencia.

| Método | Ruta | Observaciones |
|---|---|---|
| GET | `/api/health/` | Liveness sin base ni caché; 200 `{}`; sin throttling |
| GET | `/api/ready/` | Consulta base y caché; 200 `{"status":"ready"}` o 503 `error.code=not_ready`; no-store y sin throttling |
| POST | `/api/auth/register/` | email, nombre_completo, password; ANALISTA inicial; rechaza campos de privilegios |
| POST | `/api/auth/login/` | email + password; access/refresh |
| POST | `/api/auth/refresh/` | refresh |
| GET, PUT | `/api/auth/me/` | perfil propio; rol/activo read-only |
| GET | `/api/paises/` | region, search, ordering nombre/codigo_iso/poblacion |
| GET | `/api/paises/{codigo_iso}/` | datos e indicadores |
| GET | `/api/paises/{codigo_iso}/indicadores/` | tipo, anio, ordering anio/tipo/valor; search en tipo/fuente/unidad (extensión) |
| GET | `/api/paises/{codigo_iso}/tipo-cambio/` | fecha_desde, fecha_hasta (YYYY-MM-DD); ordering fecha/tasa; search en códigos de moneda/fuente (extensión) |
| POST | `/api/paises/sync-indicadores/` | ADMIN; 202 con ID, estado y estado_url; encola sin llamadas de red |
| GET | `/api/paises/sincronizaciones/` | ADMIN; última ejecución, o 204 si no existe |
| GET | `/api/paises/sincronizaciones/{uuid}/` | ADMIN; estado, progreso, intentos y resultado persistido |
| GET, POST | `/api/portafolios/` | propios+públicos; ADMIN ve todos; search y es_publico |
| GET, PUT, DELETE | `/api/portafolios/{id}/` | detalle con posiciones/métricas y ETag; PUT requiere version en JSON; DELETE requiere If-Match |
| POST | `/api/portafolios/{id}/posiciones/` | posición + version del portafolio |
| PUT, DELETE | `/api/portafolios/{id}/posiciones/{posicion_id}/` | PUT posición + version; rechaza posiciones con `fecha_salida` no nula con 400 (versión vigente). DELETE requiere If-Match del portafolio padre y conserva histórico |
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

Con `excluir_id`, disponibilidad exige permiso de edición sobre ese portafolio y
consulta los nombres de su propietario, también cuando ADMIN edita uno ajeno.
Un objeto privado ajeno no visible devuelve 404; visible sin permiso de escritura,
403. No admite elegir arbitrariamente un usuario para consultar sus nombres.

La sincronización transita PENDIENTE → EJECUTANDO → COMPLETADA/PARCIAL/FALLIDA.
`Location` y `estado_url` apuntan a su consulta. Solo existe una sincronización ADMIN
activa; repetir envío devuelve esa ejecución. Idempotency-Key conserva HTTP 202 y
el mismo ID durante cinco minutos, incluso si el trabajo termina. GET de estado
no consume el presupuesto sync2/h, pero sí user100/min. No se expone lease_token.
No asumir que cero actualizaciones es fallo: puede no haber datos nuevos. PARCIAL
incluye errores finales de proveedor o recálculo; FALLIDA indica fallo total o
interrupción no recuperable tras tres intentos.

Riesgos incluyen `calidad_datos`: conteos de indicadores externos/manuales/sintéticos/
sin origen, tasas externas/sintéticas/totales, antigüedad de cálculo y tasa,
indicadores rezagados o sin fecha, `solo_fuentes_externas`, `datos_rezagados` y
`requiere_revision`. Se derivan del snapshot histórico; no certifican exactitud.
El dashboard agrega países con datos no verificados y con datos rezagados.
Las nuevas semillas usan fuente DEMO_SINTETICO; MANUAL previo no se reclasifica.

Auditoría: GET `/api/auditoria/` es una extensión de solo lectura para ADMIN. Listado paginado, filtros `accion`, `entidad_afectada`, `usuario` y ordering `fecha`/`accion`. Los eventos de comandos sin sesión tienen `usuario: null`; los interactivos conservan el identificador del usuario.

Crear portafolio:

```json
{"nombre":"Latam propio","descripcion":"Simulación","es_publico":false}
```

Agregar posición, usando la versión obtenida de GET del portafolio:

```json
{"pais":"CO","tipo_activo":"RENTA_FIJA","monto_inversion_usd":"10000.00","fecha_entrada":"2026-11-16","notas":"Simulación","version":1}
```

La fecha es solo ejemplo; usar una fecha UTC no futura. Montos/tasas/scores son strings decimales. Crear posición incrementa versión; recuperarla en GET detalle/resumen antes de otra escritura. DELETE de posición cierra en fecha UTC actual y devuelve 400 si la entrada es hoy. DELETE de portafolio devuelve 204.

Ambos DELETE exigen `If-Match: "2"` (ejemplo de ETag fuerte; comillas obligatorias), sin body. N siempre representa la versión del portafolio padre, también al cerrar una posición. La ausencia o sintaxis inválida de cabecera devuelve 400; versión obsoleta devuelve 409 sin cambios. No se admiten comodín `*`, etiquetas débiles `W/"2"`, varias etiquetas, ni fallback a `?version=`/JSON. GET detalle y resumen exponen `ETag: "N"`; también sigue disponible `version` en JSON. CORS permite la cabecera de petición y expone ETag.

DRF sí puede leer `request.data` en DELETE (el flujo anterior lo verificaba); la migración a cabecera evita depender de cuerpos DELETE que algunos intermediarios pueden descartar. Ejemplo de petición:

```http
DELETE /api/portafolios/1/posiciones/3/
Authorization: Bearer <access>
If-Match: "2"
```

Se conserva 409 para una versión obsoleta por el contrato de este backend; no se usa 412. El formato de errores sigue siendo el mismo.

409:

```json
{"error":{"code":"conflict","message":"El registro cambió. Actualiza los datos antes de reintentar.","details":{"detail":"El registro cambió. Actualiza los datos antes de reintentar."}}}
```

Política de visibilidad: un público ajeno es consultable/exportable, no editable. No permitir que el frontend interprete público como colaborativo. Una subida del IRPC significa menor riesgo; `variacion` compara contra el cálculo anterior y `tendencia` es SUBE/BAJA/ESTABLE/SIN_HISTORICO.

## Extensiones respecto al PDF

Inventario de adaptaciones y extensiones entregadas:

- `Moneda`: normaliza monedas y corrige la FK propuesta hacia un campo no único de País.
- `LecturaAlerta`: conserva lectura independiente por usuario para alertas globales.
- `Portafolio.version`, ETag e If-Match: implementan control de concurrencia para el escenario exigido en p. 14.
- `Pais.bandera_url`: amplía el modelo para soportar bandera solicitada por la fuente externa y la vista de detalle de país.
- `search` en indicadores (tipo/fuente/unidad) y tipo de cambio (monedas/fuente): búsqueda adicional a países y portafolios, que sí exige el PDF. Está implementada y probada; previamente se anunciaba por herencia de OpenAPI pero no filtraba.
- `DashboardSummary.paises_con_irpc` y `paises_irpc_parcial`: transparencia de cobertura y datos faltantes. También se detallan factores, conteo y penalización por concentración dentro del JSON de cálculo.
- Endpoints Health, OpenAPI/Swagger y `nombre-disponible`: operación técnica, documentación y validación asíncrona exacta del nombre.
- GET `/api/auditoria/` ADMIN y `LogActividad.usuario` nullable: consulta de auditoría y procedencia de comandos de sistema según decisión P4.
- `IndiceRiesgo.clave_calculo` y `Alerta.clave_evento`: claves técnicas de idempotencia/deduplicación. Los campos de versión, detalle y cobertura no representan nuevos indicadores financieros.

`Alerta.titulo`, `Alerta.mensaje`, `Alerta.severidad` y `Alerta.tipo_alerta` **no son extensiones**: el modelo del PDF los enumera en p. 3; también soportan la UI y sus filtros. Se documentan aquí para corregir esa premisa de la observación. El resto de operaciones del contrato backend requerido se mantiene; esto no implica entregar frontend, publicación ni video.
# Controles de seguridad adicionales

La envoltura `error.code/message/details` permanece. Nuevos códigos:
`account_locked` (429 con Retry-After900), `captcha_required` (400) y
`throttled` (429 con Retry-After calculado). Credenciales inválidas401 uniforme.
Cinco fallos email/IP bloquean15min; CAPTCHA obligatorio en registro de producción
y después de tres fallos recientes/IP en login. Demo DEBUG lo desactiva; scopes
anon20/min y user100/min se mantienen. Nuevos scopes: login5/min, register3/min,
sync2/h, recalcular2/h, export_pdf10/min, mfa_verify5/min.

`GET /api/auth/captcha/` devuelve captcha_key/image_url; GET image_url retorna
imagen local. Enviar captcha_key/captcha_answer en registro o login cuando aplica.
Reto expira y se consume tras un intento, también si falla. Nunca retorna solución.

`POST /api/auth/password-change/` autenticado recibe current_password/new_password;
mínimo12 caracteres y validadores Django. Respuesta204; invalida access y todos
los refresh anteriores. Volver a iniciar sesión.

MFA ADMIN (seed sin MFA):

| Ruta POST | Entrada | Respuesta |
|---|---|---|
| /api/auth/mfa/enroll/ | ADMIN autenticado, sin cuerpo | otpauth_url y qr data:image/png;base64; conservar en privado |
| /api/auth/mfa/verify/ | code TOTP | recovery_codes (10; mostrados una vez) y habilita MFA |
| /api/auth/mfa/disable/ | code TOTP actual | 204; recovery no permite deshabilitar |
| /api/auth/mfa/verify-login/ | mfa_token y code TOTP/recovery | access/refresh |

Login ADMIN enrolado retorna `{mfa_required:true,mfa_token:...}` sin JWT. Reto5min,
ligado a contraseña y época MFA, un solo uso. TOTP6 dígitos/30s con tolerancia±1
paso y protección replay. Un recovery se consume una vez. Verificación incorrecta401;
scope excedido429. Enrolar/deshabilitar invalida sesiones anteriores.

`Idempotency-Key` opcional en POST /api/paises/sync-indicadores/ y
/api/riesgo/calcular/: ASCII visible1..128, cache DB5min por usuario/endpoint.
Misma clave/cuerpo devuelve respuesta previa sin repetir ejecución/auditoría;
mismo identificador con otro cuerpo409. Cada petición sigue contando para cuotas.
Expiración permite ejecución nueva; no reutilizar claves para otra intención.

Auth devuelve Cache-Control:no-store incluso en errores; CORS admite
Idempotency-Key e If-Match. If-Match fuerte/Decimal/UTC siguen iguales.
Producción deshabilita /api/docs/ por defecto; /api/schema/ permanece público.
OpenAPI versionado documenta unión de respuestas login, MFA, nuevos errores y
cabeceras. Angular incorpora CAPTCHA y login MFA; falta la UI de enrolamiento. Ver
[integración](INTEGRACION_SEGURIDAD.md) y [seguridad](SEGURIDAD.md).
