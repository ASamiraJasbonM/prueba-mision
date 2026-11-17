# Plan corregido de DataPulse Latam

Revisión del 17 de noviembre de 2026 contra las 20 páginas de `Prueba_Tecnica_Desarrollador.pdf`. Este documento revisa el plan pegado; no inicia la implementación ni el despliegue. Las propuestas para resolver ambigüedades se identifican como decisiones recomendadas, no como requisitos expresos del PDF.

## Correcciones al diagnóstico inicial

| Tema | Corrección y efecto en el plan | Referencia |
|---|---|---|
| Documento incompleto | El PDF tiene 20 páginas. Tareas, despliegue, evaluación, entrega y FAQ sí están disponibles. | pp. 12–20 |
| Presupuesto | Los rangos originales suman **64–81 horas**, no 60. Es necesario redistribuir y limitar extras. | Suma del plan pegado |
| Plazo | Inicio: 17-nov-2026 08:00; entrega: 20-nov-2026 18:00. Son 82 horas de calendario; las 60 horas son duración estimada de trabajo, no disponibilidad continua. El documento no explicita zona horaria. | p. 1 |
| Ponderaciones | Hay tres esquemas: partes técnicas 40/35/25; entregables 50/20/20/10; rúbrica detallada 20/25/25/15/15. No deben presentarse como una única ponderación coherente. | pp. 2, 9, 11, 13–16 |
| Tareas | Se piden al menos dos automatizadas, pero se describen tres: indicadores, recálculo IRPC y cambio diario. Conviene cubrir las tres operaciones con comandos y encadenar recálculo después de sincronizar indicadores. | pp. 11–12 |
| Seed | Faltaban mínimos precisos: 10 países completos, al menos 3 años de indicadores por país, 30 días de cambio, 3 usuarios exactos, 2 portafolios con posiciones e IRPC para todos. | p. 13 |
| Video | Es obligatorio un video de **5–8 minutos**; figura como 10% de los entregables. Debe tener tiempo reservado. | p. 14 |
| Históricos | Los gráficos requieren 5 años y 30 días. El mínimo del seed económico es 3 años: cargar 5 cuando existan, representar faltantes explícitamente. | pp. 10, 13 |
| Integraciones | Se exigen en el cuerpo técnico, pero la FAQ llama bonus a la sincronización externa y permite seed si las APIs fallan. Implementarlas con tolerancia a fallos y documentar cualquier indisponibilidad; no asumir que pueden omitirse sin impacto. | pp. 6, 12, 19 |
| Concurrencia | Faltaba el escenario de edición simultánea del portafolio público y mensajes de conflicto. | p. 14 |
| Entrega | Repositorio público con commits incrementales, README completo, URLs HTTPS, datos demo y enlace al video. El email lleva una descripción de máximo 300 palabras. | pp. 13–17 |

## Inconsistencias y decisiones antes de migrar

1. **IRPC: fórmula frente al ejemplo.** El código penaliza inflación de 9,2% con −10, pero el ejemplo aplica −25. Manteniendo los otros datos del ejemplo, incluidos sus tres indicadores negativos, el score económico es 60 y el IRPC es `60 × 0,40 + 90 × 0,30 + 80 × 0,30 = 75`, riesgo BAJO; el documento muestra 69, MODERADO. Recomendación: implementar los umbrales del pseudocódigo y registrar esta discrepancia en el README y las pruebas (pp. 7–9).
2. **Indicadores negativos sin definición.** `contar_indicadores_en_riesgo` no tiene umbrales ni universo definidos. Propuesta: contar una vez cada indicador económico con penalización según los umbrales explícitos; documentar la lista exacta. Esto requiere una decisión y puede cambiar la reproducción del ejemplo (p. 8).
3. **Datos ausentes.** El IRPC debe funcionar y señalar faltantes (p. 14). Propuesta mínima: omitir la penalización que no puede evaluarse, conservar pesos y marcar cálculo parcial con fuentes, fechas y campos faltantes en `detalle_calculo` y UI. Este criterio puede elevar el score; debe quedar visible y no presentar el resultado como completo.
4. **Año del PIB y decimales.** Usar los dos últimos años consecutivos disponibles, evitando dividir por cero; marcar ausencia si no existen. Aplicar intervalos continuos: ≥75 BAJO, ≥50 MODERADO, ≥25 ALTO y <25 CRITICO, sin redondear antes de clasificar. Ambas son decisiones para completar ambigüedades de pp. 8–9.
5. **FK de monedas.** `Pais.moneda_codigo` no está definido como único. Una FK hacia él exigiría unicidad y dificultaría compartir moneda. Recomendación: entidad `Moneda(codigo PK)` y FKs desde País y TipoCambio. Añadir unicidad `(moneda_origen, moneda_destino, fecha)` y conservar el contrato de país de la API (pp. 2–3).
6. **Sentido de la tasa.** El endpoint con base USD devuelve monedas locales por USD; si se persiste origen local → destino USD, almacenar el inverso. Definir variación sobre la tasa persistida y depreciación con el signo correcto. La depreciación acumulada se obtiene de tasas extremas o composición multiplicativa, no de sumar porcentajes. Documentar desviación poblacional o muestral y qué ocurre con menos de dos observaciones (pp. 6–7).
7. **Alertas globales y lectura.** Un único booleano `leida` global permitiría que un usuario marque la alerta para todos. Propuesta: relación de lectura por usuario para alertas globales, manteniendo el contrato de lectura individual. Deduplicar alertas al reintentar la misma sincronización (pp. 3, 5).
8. **Propiedad y concurrencia.** Público se define como visible, pero el escenario menciona dos usuarios editando. Propuesta predeterminada: creador y ADMIN editan; otros usuarios solo consultan. Toda edición autorizada usa versión o fecha de modificación y responde 409 ante conflicto. Serializar cambios de posiciones por portafolio para proteger límites ante concurrencia. Documentar esta interpretación (pp. 3, 14).
9. **Cierre y totales.** Definir posiciones activas como `fecha_salida IS NULL`; propuesta: calcular exposición y límites sobre ellas y mostrar histórico cerrado aparte. DELETE de posición fija salida y conserva el registro; no puede violar salida > entrada si se abre y cierra el mismo día. Rechazar ese caso con mensaje claro hasta definir otra política; no inventar una fecha futura (pp. 4–5, 11).
10. **Roles.** El registro y la edición de perfil no deben permitir autoasignarse ADMIN. Definir rol inicial y campos editables; aplicar permisos también a posiciones, exportación y acceso a portafolios privados. El PDF explicita la prohibición de creación/edición de portafolios por VIEWER, pero no completa toda la matriz (pp. 4–5).
11. **Proveedores.** La URL REST Countries incluye `contries`; los endpoints, acceso, cobertura histórica y condiciones de los tres proveedores deben verificarse al implementar. Esta revisión documental no confirma su funcionamiento actual. No se pueden obtener 30 días reales consultando únicamente una tasa actual (p. 6).

El PDF admite máximo dos consultas de aclaración por email (pp. 19–20). Si se usan, las más útiles son: fórmula/indicadores negativos y permisos/concurrencia en portafolios públicos. Esta revisión no envía correos.

## Contrato mínimo de la API

Son **31 operaciones método + ruta**, sin contar extensiones propuestas. No bastan 31 URLs distintas: varias rutas tienen más de un método.

| Grupo | Operaciones requeridas |
|---|---|
| Autenticación (5) | POST `/api/auth/register/`, POST `/api/auth/login/`, POST `/api/auth/refresh/`, GET y PUT `/api/auth/me/` |
| Países (5) | GET `/api/paises/`, GET `/api/paises/{codigo_iso}/`, GET `/api/paises/{codigo_iso}/indicadores/`, GET `/api/paises/{codigo_iso}/tipo-cambio/`, POST `/api/paises/sync-indicadores/` |
| Portafolios (10) | GET y POST `/api/portafolios/`; GET, PUT y DELETE `/api/portafolios/{id}/`; POST `/api/portafolios/{id}/posiciones/`; PUT y DELETE `/api/portafolios/{id}/posiciones/{posicion_id}/`; GET `/api/portafolios/{id}/resumen/`; GET `/api/portafolios/{id}/export/pdf/` |
| Riesgo (4) | GET `/api/riesgo/`, GET `/api/riesgo/{codigo_iso}/`, GET `/api/riesgo/{codigo_iso}/historico/`, POST `/api/riesgo/calcular/` |
| Alertas (4) | GET `/api/alertas/`, PUT `/api/alertas/{id}/leer/`, PUT `/api/alertas/leer-todas/`, GET `/api/alertas/resumen/` |
| Dashboard (3) | GET `/api/dashboard/resumen/`, GET `/api/dashboard/mapa/`, GET `/api/dashboard/tendencias/` |

Completar payloads, errores y filtros antes de consumirlos desde Angular. Incluir severidad en el filtro de alertas, solicitado por la vista aunque no aparezca en la tabla de endpoints. La validación asíncrona de nombre necesita una consulta exacta por usuario y exclusión del portafolio editado: extender el listado con parámetros documentados o añadir una operación específica; la búsqueda textual paginada por sí sola no garantiza unicidad.

Transversal (pp. 5, 12): paginación configurable con default 20 en listados, ordering, búsqueda en países/portafolios, errores consistentes en español, throttling 100/min autenticados y 20/min anónimos, permisos por rol, logging estructurado, auditoría CRUD y middleware de requests con método, path, usuario y duración. Definir el formato paginado de series para que los gráficos no pierdan puntos al recibir solo la primera página.

## Ejecución propuesta: 60 horas de trabajo

Es un presupuesto objetivo con alcance exigente, no una garantía. Mantener un flujo vertical y validar integración en cada fase; el frontend no debe esperar a que termine todo el backend.

| Fase | Horas | Trabajo y criterio de salida |
|---|---:|---|
| 0. Contrato y base ejecutable | 3 | Registrar decisiones anteriores, contrato y estructura backend/frontend; variables, health check y primera publicación mínima si hay acceso al hosting. Fijar dependencias compatibles y seed pequeño. |
| 1. Modelos, auth y permisos | 8 | Usuario AbstractUser con email, modelos normalizados, migraciones, constraints, índices, Django Admin, JWT, roles y alcance de consultas. Recorrido login → listado de países desde Angular. |
| 2. Datos e integraciones | 7 | Clientes de las tres APIs, timeouts, manejo de fallos parciales, upserts y comandos. Seed reproducible independiente de red; avanzar hasta mínimos completos de entrega. |
| 3. IRPC, alertas y dashboard API | 6 | Funciones verificables con umbrales, faltantes y detalle; históricos; tres operaciones de background encadenadas; alertas y KPIs/mapa/tendencias. |
| 4. Portafolios y PDF | 7 | CRUD y borrado lógico, posiciones, todas las validaciones, permisos, conflicto de edición, resumen y PDF tabular. Integrar flujo crear → agregar → exportar. |
| 5. Completar Angular | 14 | Material, strict, módulos lazy, formularios reactivos, guards, interceptors y estado observable. Terminar dashboard, detalle país, portafolios, alertas, mapa, gráficos, polling 30 s, estados vacíos/error/carga y 404. |
| 6. Consolidar despliegue | 5 | Actualizar lo publicado desde fase 0; HTTPS, CORS, persistencia, seed, ejecución de tareas y comprobación de las dos URLs y tres usuarios. No depender de una supuesta oferta gratuita sin verificarla. |
| 7. QA, documentación, video y margen | 10 | Escenarios críticos, revisión 1920/768, README con arquitectura/ER y ejecución reproducible, decisiones, endpoints, URLs y credenciales. Grabar y verificar video 5–8 min; revisar enlaces y preparar texto de entrega. Reservar dentro de estas horas margen para fallos. |
| **Total** | **60** | |

En cada fase: commits incrementales, documentación y verificación del recorrido afectado. Las fases representan bolsas de tiempo; integrar y publicar avances atraviesa todo el trabajo. No se ha publicado código ni creado infraestructura durante esta revisión.

## Condiciones que no deben desaparecer al simplificar

- Posición: USD 1.000–10.000.000, entrada no futura, notas ≤200, país con autocomplete, tipo requerido; máximo dos activas por país/tipo, prohibición MONEDA si moneda USD y total ≤USD 50.000.000. Validar también en backend y en edición, no solo al crear.
- Portafolio: nombre 3–100, único por usuario con validación async, descripción ≤500 y contador, visibilidad pública y confirmación de borrado.
- Dashboard: mapa por color, cuatro KPIs, ranking de diez con variación/tendencia y comparación de tres países en cinco años.
- País: bandera e información completa, tarjetas e históricos económicos, cambio 30 días, desglose de tres scores + compuesto e histórico IRPC. Añadir almacenamiento de bandera al modelo propuesto.
- Alertas: cinco disparadores del PDF, filtros de tipo/severidad/lectura, lectura individual/masiva y badge 30 s. Decidir y documentar si el umbral cambiario >3% usa magnitud absoluta; el PDF no lo precisa.
- Resiliencia: una API o un país fallido no cancela el resto; mantener datos anteriores, registrar inicio/fin/errores y mostrar datos faltantes. No fabricar históricos silenciosamente: etiquetar datos estáticos de demostración y su procedencia.
- Frontend: 401 redirige a login con mensaje; errores HTTP por snackbar y caso de desconexión. Ocultar acciones sin permiso y protegerlas en servidor.
- Mantener el stack obligatorio Django 4+/DRF y Angular 12+/Material. PostgreSQL es preferido; SQLite se acepta incluso desplegado según FAQ, pero debe persistir y las garantías de concurrencia necesitan verificarse en el motor elegido.

Simplificaciones razonables: Material básico, mapa sencillo interactivo con indicadores, PDF tabular sin gráficos y estado con BehaviorSubject. Posponer extras: WebSockets, XLSX, PDF con gráficos, NgRx, CI/CD elaborado y Docker si comprometen lo obligatorio. Tests y documentación interactiva suman puntos adicionales; las verificaciones críticas siguen siendo útiles para evitar fallos funcionales.

## Verificación y entrega

Pruebas prioritarias: umbrales IRPC y clasificación decimal; ejemplo corregido; indicadores faltantes; permisos por rol/propiedad; límites de posiciones en creación y edición; conflictos concurrentes; cierre con fechas válidas; lectura de alertas globales por usuario; reintentos idempotentes; proveedor caído y JWT expirado. Comprobar un recorrido completo desde el navegador y en ambas resoluciones exigidas.

Seed de aceptación (p. 13): CO, BR, MX, AR, CL, PE, EC, UY, PY y PA con regiones/coordenadas del documento; seis indicadores con al menos tres años por país; treinta días de cambio; dos portafolios con posiciones e IRPC de los diez países. Usar los usuarios `admin@datapulse.com`, `analista@datapulse.com` y `viewer@datapulse.com` con contraseña demo `DataPulse2026!`, indicada expresamente para la prueba; no reutilizarla para infraestructura.

Checklist final:

- Repositorio público: `/backend`, `/frontend`, `.env.example`, `.gitignore` y commits incrementales; no exigir Git Flow si no se eligió usarlo.
- README: arquitectura, diagrama ER, decisiones y alternativas, instalación reproducible, comandos de tests/seed/tareas, endpoints, manejo de errores/logs, limitaciones, URLs y credenciales demo.
- Frontend y backend públicos por HTTPS, CORS correcto, datos persistentes y tres sesiones demo verificadas.
- Video accesible de 5–8 minutos con login, dashboard, creación/posiciones, país, alertas, sincronización ADMIN y explicación de arquitectura.
- Texto de entrega ≤300 palabras con enlaces a repositorio, frontend, backend y video; preparar no implica enviar correo.
- Preparar defensa de 45–60 minutos: explicar decisiones, ciclo del request, hacer un cambio y diagnosticar un error en vivo (pp. 17–18).

Los dos puntos de evaluación más fáciles de subestimar en el plan original son la documentación y el video. Deben completarse dentro del presupuesto, junto con el despliegue funcional, y no tratarse como extras al terminar de programar.
