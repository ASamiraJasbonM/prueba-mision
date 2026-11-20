# Verificación de integración frontend / backend

> Verificación histórica del 17 de noviembre. Conserva sus resultados y límites
> originales; la automatización E2E y el despliegue posteriores se describen en
> [ESTADO_ACTUAL](ESTADO_ACTUAL.md) y [E2E](E2E.md).

Fecha: 17 de noviembre de 2026 (America/Bogota).

Se verificó el contrato HTTP y la interacción de la SPA Angular con Django/DRF real. Las escrituras se ejecutaron sobre una copia SQLite aislada en `tmp/`, sin modificar los datos de demostración originales. No se cambiaron modelos, migraciones, lógica de negocio ni settings del backend.

## Entorno

- Desarrollo existente: frontend `127.0.0.1:4200`, proxy `/api` hacia backend `127.0.0.1:8000`.
- Comprobación aislada: build de producción servido en `127.0.0.1:4201`, `/api` reenviado al servidor Django `127.0.0.1:8001` con la copia SQLite. Se utilizaron los archivos reales de `frontend/dist/datapulse/browser`, sin mocks de respuestas del servidor.
- La URL relativa `/api/` se toma de los environments; la configuración de otro origen y CORS en nube no queda probada por esta ejecución local.

## Resultados HTTP

**110 comprobaciones aprobadas, 0 fallidas, sobre 66 peticiones HTTP reales.** Los 400/401/403/404/409 esperados forman parte de las pruebas negativas, no son fallos de ejecución.

| Flujo | Resultado observado |
|---|---|
| Conexión y autenticación | Health por proxy y backend directo; login/perfil ADMIN, ANALISTA y VIEWER; refresh válido; errores uniformes al no tener sesión o enviar credenciales inválidas. |
| Países y paginación | Páginas distintas, búsqueda, detalle, indicadores filtrados, tasas por rango UTC; decimales serializados como strings. |
| Riesgo y dashboard | Resumen/cobertura, mapa, detalle e histórico; ranking IRPC descendente; quince puntos de tendencias con valor string o null. |
| Portafolios | Alta, nombre disponible/duplicado, privado oculto a otro usuario, publicación, detalle y ETag, edición y resumen exacto. |
| Posiciones | Alta y edición con decimal exacto; rechazo de monto inferior, entrada futura y MONEDA para país USD; cierre UTC e imposibilidad de editar una cerrada. |
| Concurrencia | 409 ante versión antigua sin mutaciones; DELETE requiere ETag fuerte con comillas, sin cuerpo; desaparición tras borrado. |
| Permisos | VIEWER no crea/edita; ANALISTA no edita un público de otro propietario; controles administrativos restringidos. |
| PDF | VIEWER puede exportar público; respuesta application/pdf, attachment y contenido con firma PDF. |
| Alertas | Filtros, lectura personal, lectura global independiente para cada usuario, leer todas y resumen actualizado. |
| Registro | Cuenta creada con rol ANALISTA, sin elevar privilegios. |

## Comprobaciones desde la interfaz

- Registro → login → perfil real → dashboard, con 201/200/200 y rol ANALISTA.
- Creación de portafolio desde formulario y validación asíncrona de nombre.
- Monto 999.99 bloqueado en formulario; entrada `1,234.56` enviada como string `1234.56`, presentada como `1.234,56` y reflejada en el resumen.
- Edición de posición a `2345.67`; POST/PUT incluyen la versión del padre y cada escritura va seguida de GET del detalle.
- Cambio simultáneo externo a la UI: el formulario recibió 409, releyó datos vigentes y avisó; solo un reenvío explícito guardó con la nueva versión.
- Cierre desde diálogo: `DELETE` con `If-Match: "5"`, cuerpo null, HTTP 200, relectura y total activo cero. Borrado del portafolio con `If-Match: "6"` y HTTP 204.
- Descarga PDF desde botón con HTTP 200.
- Lectura de alerta y de todas desde botones: GET de listado/resumen y badge actualizado a cero; la misma alerta global siguió sin leer para VIEWER.
- Polling de resumen medido entre peticiones: 29,999; 30,009; 29,997 y 29,992 segundos.
- VIEWER no ve creación y la ruta `/portafolios/nuevo` redirige a acceso restringido.
- ADMIN ve las acciones administrativas; recalcular riesgo respondió 200 y el informe de la UI indicó diez registros actualizados sin errores. El ranking se volvió a consultar.
- Access inválido con refresh válido: GET perfil 401 → POST refresh 200 → GET perfil 200, sin perder sesión.
- Ambos tokens inválidos: sesión borrada y redirección al login.

## Hallazgos y correcciones

1. **Ruta perdida al vencer sesión durante una navegación inicial.** La UI tomaba `router.url`, que aún era `/`, en vez de la URL del enlace que se estaba abriendo. Se utiliza la navegación en curso (finalUrl/extractedUrl) y se conserva el fallback a la ruta activa. Se añadió regresión de interceptor y se volvió a comprobar un enlace de país en el build real.
2. **Mapa ausente en producción.** La importación dinámica de Leaflet expone solo `default` en el bundle CommonJS de producción, mientras desarrollo permite acceder a exports nombrados. Se normaliza la importación para ambos formatos y se comprueba el dibujo con el módulo Leaflet real, además del navegador contra el build final.

## Regresión final

- Build de producción correcto después de las dos correcciones (entrada 541,62 KB, transferencia estimada 139,16 KB).
- **25 pruebas frontend aprobadas**, incluidas una regresión de navegación con sesión vencida y una prueba que importa Leaflet real y verifica el polígono y su color.
- En el build final, `/paises/CO?verification=final` redirige al login conservando exactamente esa ruta; tras autenticarse vuelve a Colombia con seis indicadores y dos gráficos.
- Mapa de producción con diez polígonos antes y después de recalcular; clic sobre Argentina abre `/paises/AR` y consulta detalle, tasas e histórico de riesgo reales. El segundo recálculo idempotente reportó cero cambios sin errores.

## Límites de esta verificación

- Backend local SQLite: 61 pruebas ejecutadas, 59 aprobadas y 2 omitidas por requerir PostgreSQL. No se repitió PostgreSQL en esta revisión.
- No se ejecutó la sincronización contra proveedores externos: se verificó su restricción de permisos. El recálculo local ADMIN sí se ejecutó sobre la copia aislada.
- No valida despliegue cloud, HTTPS, CORS entre dominios ni disponibilidad/credenciales de los proveedores externos.
- Las pruebas de navegador fueron comprobaciones de esta revisión, sin añadir una suite Cypress/Playwright.

Los servidores temporales de verificación (4201/8001) se detuvieron al terminar; la aplicación habitual en 4200 y su API en 8000 continúan disponibles. Los artefactos de comprobación y la copia de datos quedaron en `tmp/`, fuera del versionado.
