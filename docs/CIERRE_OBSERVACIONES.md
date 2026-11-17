# Cierre de observaciones del backend

Las correcciones se aplicaron en orden P1–P9, sin reescribir el proyecto, en commits locales separados de `feat/backend-datapulse`. Las evidencias siguientes contienen la salida completa de cada comando y su código de salida. El último bloque reúne los cinco comandos globales solicitados.

| Observación | Resultado | Commit local | Evidencia completa |
|---|---|---|---|
| P1 | Frase canónica en README/arquitectura y bordes 74.994/74.995/74.999 | a354c78 | [P1](observaciones/P1.md) |
| P2 | Tabla 69/75/72; composición histórica y cálculo real de tercera fila probados | 955300c | [P2](observaciones/P2.md) |
| P3 | Conteo de seis factores, lista/valores/penalizaciones persistidos y escenarios probados | 561ff18 | [P3](observaciones/P3.md) |
| P4 | Política única usuario null; consulta de auditoría solo lectura ADMIN | 5ce5bfe | [P4](observaciones/P4.md) |
| P5 | PUT cerrado devuelve 400 sin cambios; política de histórico explícita | 1349abc | [P5](observaciones/P5.md) |
| P6 | If-Match obligatorio en ambos DELETE, ETag, CORS, 409 y OpenAPI | 7983d22 | [P6](observaciones/P6.md) |
| P7 | Inventario de extensiones fiel al PDF; search anunciado ahora filtra | 196e993 | [P7](observaciones/P7.md) |
| P8 | Frontend, despliegue y video explícitamente fuera del alcance backend | 29b26f4 | [P8](observaciones/P8.md) |
| P9 | Check, deriva de migraciones, suite completa, OpenAPI y política numérica | Commit que incorpora este cierre | [P9](observaciones/P9.md) |

## Precisiones necesarias sobre las observaciones recibidas

- P3: la recesión −3% resta 30 por su penalización directa y 5 adicionales por concentración al score de estabilidad. El IRPC pasa de 72 a 61,50, no a 67: esos 35 puntos de estabilidad pesan 30%. El factor adicional aislado resta 1,50 al IRPC. Los tests fijan la fórmula sin introducir un ajuste artificial de cinco puntos al compuesto.
- P4: se mantiene nullable como adaptación explícita del modelo, sin usuario técnico ni migración. El endpoint de auditoría se añadió para verificar serialización y acceso según esta observación.
- P5: no se afirma que una posición cerrada pueda eliminarse físicamente. Esa ruta no existe y DELETE debe conservar el histórico. Para registrar correcciones se crea una posición nueva referenciando la anterior en notas.
- P6: DRF sí podía leer JSON en DELETE; los tests anteriores lo demostraban. La cabecera mejora interoperabilidad y evita depender de cuerpos DELETE. Falta/sintaxis inválida devuelve 400; versión antigua conserva 409 por el contrato solicitado.
- P7: título, mensaje, tipo y severidad de Alerta ya aparecen en el modelo del PDF (p. 3). No se etiquetan falsamente como extensiones. La búsqueda en históricos estaba anunciada pero era inefectiva; ahora tiene campos y pruebas de filtrado.
- P8: los porcentajes de partes técnicas y entregables pertenecen a esquemas distintos. La documentación no suma esos porcentajes como cobertura ni promete una nota obtenida.

## Límites de la evidencia

Los tests de constraints aplican migraciones en una base limpia; el chequeo de migraciones detecta cambios de esquema sin generar archivos. Las pruebas de HTTP comprueban errores uniformes y permisos; las de If-Match comprueban versiones antiguas y ausencia de efectos. La política estática revisa producción y migraciones sin confundir `parse_float=Decimal` con una llamada `float()`.

SQLite no prueba bloqueos de filas ni la precisión numérica de PostgreSQL. Las dos pruebas específicas de ese motor se identifican como omitidas en la salida de la suite, sin presentarlas como aprobadas. La verificación con PostgreSQL y proveedores reales sigue pendiente; no se ejecutó despliegue ni se añadieron fases de frontend/video fuera del alcance acordado.

Los snapshots de código y resultados 0–10 son históricos; las observaciones documentan las revisiones posteriores. El contrato vigente es [API.md](API.md) y [openapi.yaml](openapi.yaml), con reglas canónicas en [README](../README.md).
