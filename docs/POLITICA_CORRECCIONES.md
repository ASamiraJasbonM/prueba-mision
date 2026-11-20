# Política de corrección y archivo — CORRECCION_V1

Decisión de producto: se recomienda un plazo de **24 horas** para corregir una
posición creada por error o duplicada. No es una regla legal ni una exigencia del
PDF. El abandono de una iniciativa se resuelve archivando el portafolio, conservando
sus datos. El plazo se aplica al borrado físico de posiciones, no al archivo.

| Caso | Operación | Conservación |
|---|---|---|
| Error al crear el portafolio, idea duplicada o decisión de no continuar | Archivar en cualquier momento | Portafolio inactivo, posiciones e historial conservados |
| Error/duplicado de una posición abierta dentro de 24 horas | Corrección con motivo y confirmación | Fila retirada; snapshot completo cifrado y evento de auditoría conservados |
| Posición cerrada o fuera de plazo | No se permite borrado físico | Cierre normal o nueva posición correctiva con referencia en notas |
| Posición previa a la migración sin creación acreditada | No se permite borrado físico | No se inventa una fecha de creación para habilitar la corrección |

## Reglas de aplicación

- Dueño ANALISTA o ADMIN; VIEWER no modifica. ADMIN está sujeto al mismo plazo.
- El reloj es la fecha de creación del registro en el servidor, en UTC. La fecha
  de entrada económica y las ediciones no reinician el plazo. En el instante
  exacto del vencimiento ya no se permite la corrección.
- La posición debe seguir abierta. El cierre exigido por el PDF permanece en
  DELETE /posiciones/{id}/ y exige salida posterior a entrada.
- La corrección usa DELETE /posiciones/{id}/eliminar/?motivo=ERROR_CREACION o
  motivo=DUPLICADO. Motivo obligatorio; If-Match con versión vigente, sin body.
- El archivo del portafolio usa DELETE /portafolios/{id}/?motivo=...; acepta
  ERROR_CREACION, DUPLICADO, DESISTIMIENTO y ARCHIVO. La UI obliga a elegir;
  consumidores anteriores sin motivo conservan compatibilidad con ARCHIVO.
- El servidor bloquea el portafolio, verifica permisos/plazo/versión y ejecuta
  evidencia, eliminación y aumento de versión en una sola transacción. Un fallo
  de cifrado o auditoría revierte toda la operación. Un conflicto devuelve 409.
- El plazo se configura con POSITION_CORRECTION_HOURS (24 por defecto, rango
  técnico 1–168). Cualquier cambio debe revisarse como política de producto;
  el evento conserva versión de política, horas y límite UTC aplicados.

## Evidencia y acceso

La auditoría de corrección registra actor, instante UTC, entidad/id, motivo,
versión anterior/nueva y un snapshot cifrado con FIELD_ENCRYPTION_KEY: país,
portafolio, tipo de activo, monto decimal exacto, fechas, notas e id. La cadena
HMAC protege el evento contra alteraciones detectables. Las notas no se copian
en claro a los logs ni se expone descifrado en la API.

El snapshot no es un botón de deshacer. No se añade recuperación automática ni
se promete restauración al usuario. La conservación de evidencia usa el historial
de auditoría existente; no se añade un borrado automático de esos eventos. La
custodia de la clave es necesaria para poder revisarlos en una operación autorizada.

El archivo no libera el nombre reservado por usuario. Se puede corregir nombre y
descripción antes de archivar o crear otro nombre. DUPLICADO es un motivo declarado,
no una búsqueda de coincidencias contra portafolios privados de otras personas.

## Mensajes sugeridos y comportamiento implementado

Archivo: «El portafolio dejará de estar disponible; sus posiciones e historial se
conservan». Ofrecer motivos «Error de creación», «Duplicado», «Decisión de no
continuar» y «Archivo de portafolio».

Corrección: mostrar fecha límite UTC, motivo obligatorio, confirmación y cancelación;
explicar que se retira la posición, se conserva evidencia cifrada y no hay deshacer
automático. Fuera de plazo/cerrada/sin creación acreditada: deshabilitar Eliminar y
explicar que se debe conservar el historial y usar el cierre.

## Validación

Regresiones de permisos, propietario/portafolio incorrecto, versión obsoleta,
vencimiento, posición cerrada, creación desconocida, cifrado y rollback. Prueba de
migración que conserva los registros previos sin plazo retroactivo. E2E desktop y
tablet para cancelación, motivo, corrección y bloqueo de posiciones cerradas.
