# DataPulse Latam · Frontend

SPA Angular 20, Angular Material, TypeScript estricto, componentes standalone con OnPush y rutas lazy. Interfaz clara, navegación verde oscuro, tipografía local DM Sans / Source Serif 4. El backend se consume sin modificar su código, migraciones, pruebas ni configuración.

## Ejecutar

Requisitos: Node 22.12 o superior de la rama 22 y npm. Dependencias reproducibles en `package-lock.json`.

```powershell
cd frontend
npm ci
npm start
```

Abrir http://127.0.0.1:4200. Iniciar el backend en http://127.0.0.1:8000 siguiendo el README de la raíz. El proxy de desarrollo redirige `/api` a esa dirección.

Usuarios demo (requieren los datos semilla del backend): `admin@datapulse.com`, `analista@datapulse.com`, `viewer@datapulse.com`; contraseña `DataPulse2026!`.

## Etapas implementadas

1. **Base y acceso:** Angular Material, tema responsive, login/registro reactivos, sesión JWT, restauración desde `/auth/me/`, renovación compartida para solicitudes concurrentes y cierre de sesión. Guards funcionales de autenticación y rol; interceptores JWT, errores y loading. Auth, alertas y loading exponen BehaviorSubject/Observable; los componentes usan signals para estado local.
2. **Panorama:** KPIs, cobertura parcial, mapa Leaflet, ranking de diez países por IRPC descendente (mayor índice = menor riesgo), variación/tendencia y comparación de tres países durante cinco años. Acciones administrativas para sincronizar/recalcular y mostrar el informe devuelto.
3. **Países:** búsqueda/región, paginación, seis indicadores con fuentes/años, históricos, cambio USD por unidad local de los últimos 30 días UTC, scores e histórico completo de riesgo, faltantes y fuentes del cálculo.
4. **Portafolios:** propios, públicos y vista administrativa; creación/edición con nombre asíncrono; posiciones con autocompletado de país, importes y reglas exactas, edición/cierre, resumen del servidor, distribución por país/activo y exportación PDF. Confirmación de eliminación/cierre. Posiciones cerradas permanecen de consulta.
5. **Alertas:** filtros, paginación, lectura individual/todas y polling cada 30 segundos del badge y del listado abierto. El backend conserva lectura por usuario, incluidas alertas globales.
6. **Verificación:** Karma/Jasmine para autenticación, guards, interceptores, paginación, polling, concurrencia, importes y formulario de posición; build de producción y comprobación visual con API local. No se añadió una suite E2E.

## Contrato y decisiones

- `environment.ts` y `environment.prod.ts` definen `apiUrl`. Por defecto usan `/api/`. Para nube, cambiar `environment.prod.ts` y habilitar el origen del frontend en el backend. El servidor estático debe devolver `index.html` para las rutas de la SPA. `ng serve` es para desarrollo.
- La sesión guarda únicamente los tokens en localStorage; los permisos proceden del perfil consultado al servidor. Las respuestas tardías de una sesión anterior no pueden reemplazar tokens/perfil de otra. VIEWER consulta y exporta; solo ADMIN o ANALISTA propietario puede escribir. Público no significa colaborativo.
- El cliente envía versión en POST/PUT de escritura y **`If-Match: "2"`**, con comillas, en DELETE sin body. Relee el detalle después de escribir y ante 409. Un 409 requiere revisar y reenviar explícitamente; nunca se reintenta una escritura automáticamente. Si falla la relectura, bloquea otra escritura hasta recuperar una versión vigente.
- El endpoint de disponibilidad consulta al usuario solicitante. Al editar como ADMIN un portafolio de otro propietario se omite esa comprobación asíncrona, porque no admite `usuario` como parámetro. Se conserva la validación de unicidad del PUT del backend, que sí usa al propietario real.
- Los importes se mantienen como strings decimales. Validaciones/sumas monetarias usan céntimos BigInt; no se emplea punto flotante para decisiones de negocio. Los separadores admitidos en entradas son `1234.56` o `1,234.56`. La presentación usa separadores españoles y no modifica el valor enviado.
- Chart.js se integra directamente, alternativa permitida por el PDF, sin wrapper adicional. La conversión validada a number se limita a dibujar gráficos. `null` conserva huecos (`spanGaps: false`); las tablas accesibles distinguen sin dato y cero.
- Leaflet 1.9.4 estable se importa de forma lazy; GeoJSON local de diez países (22 KB), sin teselas ni claves externas. Cartografía de [Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/) de dominio público, extraída del [GeoJSON oficial](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson). El color procede de la API.
- Todo formulario, incluidos filtros, es reactivo. Fechas de posiciones/cambio se tratan como fechas UTC. Tablas anchas tienen scroll local; breakpoints cubren 1920/1024/768 y móviles. Los gráficos ofrecen tabla de datos alternativa y el ranking permite llegar a cada país sin utilizar el mapa.
- Angular 20 satisface Angular 12+. Se utilizan rutas `loadChildren` y `loadComponent`, sin NgRx. El shell se compone con HTML semántico y CSS responsive; controles, tablas, formularios y diálogos son de Angular Material.
- Presupuesto inicial: advertencia 600 KB / error 1 MB (incluye Angular Material). Leaflet y Chart.js se descargan por demanda. Leaflet estable usa CommonJS; la excepción está declarada explícitamente en Angular.

## Verificar

```powershell
npm run build
npm run test:ci
npm audit --omit=dev
```

Karma requiere Chrome/Chromium. Si no está en la ruta habitual:

```powershell
$env:CHROME_BIN = 'C:\ruta\a\chrome.exe'
npm run test:ci
```

La auditoría de producción del 17/11/2026 reporta **0 vulnerabilidades**. La cadena de herramientas de desarrollo (Angular CLI/build y Karma) presenta 33 avisos transitivos: 14 moderados y 19 altos, principalmente glob/minimatch/picomatch. `npm audit fix` no ofrece una corrección compatible completa; no se aplicó `--force`, que propone bajar Angular CLI a 16 o cambiar Karma. Mantener el servidor de desarrollo en loopback y revisar actualizaciones compatibles antes de exponer herramientas de desarrollo. Estos paquetes no forman parte del JavaScript de producción.

No se añadieron secretos ni servicios externos de mapas. El despliegue backend y las pruebas E2E quedan fuera del alcance solicitado.

## Resultado local de verificación

17/11/2026: **25 pruebas Karma/Jasmine aprobadas**, build de producción correcto (entrada aproximada 542 KB / 139 KB transferidos), sin advertencias de presupuesto. Comprobación manual con API real: login de analista y viewer, dashboard/mapa/gráficos, detalle de Colombia, creación de portafolio temporal, alta de posición USD 1.234,56, cierre con fecha UTC, exportación PDF HTTP 200 y eliminación del portafolio temporal. VIEWER bloqueado en `/portafolios/nuevo` y sin controles de escritura en un portafolio público. No se añadió una suite E2E.

Viewport verificado en navegador: **1920×1080 y 768×1024 CSS px**, sin desbordamiento horizontal; mapa con diez geometrías y gráfico renderizado, sin errores de consola. Revisión independiente de las correcciones de sesión/ranking sin hallazgos sustantivos pendientes.

## Corrección responsive y consulta de gráficas

- La página crece verticalmente y permite llegar al pie mediante scroll. La navegación tiene scroll propio en pantallas de poca altura y se convierte en menú desplegable hasta 1024 px, con cierre, fondo y Escape.
- Paneles, títulos y controles se ajustan al ancho disponible. Las tablas conservan todas sus columnas con scroll horizontal local y una indicación visible en móvil.
- Las gráficas de líneas tienen títulos de ejes X/Y según año, fecha UTC y unidad; cursor con líneas guía, tooltip y panel de valores seleccionados. Funcionan con mouse, toque y teclado (←/→, Inicio/Fin). Los gráficos de distribución muestran categoría y monto, sin ejes cartesianos.
- Las tasas muy pequeñas usan notación científica en el eje para evitar presentarlas como cero; el tooltip/panel conserva hasta doce decimales. Los valores ausentes se identifican como “Sin dato”.
- Comprobación manual de dashboard, país y portafolio en móvil/tablet; anchos 320, 390, 768 y 1920 CSS px, incluyendo altura de 480 px para verificar el scroll de navegación. Pruebas adicionales de títulos de ejes, teclado, cero/faltantes, distribución y ticks de tasas pequeñas.

## Integración verificada

La [revisión de integración](../docs/INTEGRACION_FRONTEND_BACKEND.md) documenta 110 comprobaciones HTTP aprobadas, flujos de UI contra Django real y dos correcciones: carga de Leaflet en producción y conservación del enlace original tras vencer la sesión. Las escrituras de verificación usan una copia aislada de la base.

## Docker y CI

La imagen usa Node 22 slim en el builder y nginx-unprivileged estable en runtime, ambos fijados por digest. Las versiones verificadas son Node 22.23.5 y nginx 1.30.6. Se eligió una rama nginx mantenida en lugar de 1.27; los paquetes Alpine de esa base se actualizan con `apk upgrade --no-cache` antes de cambiar a nginx (UID 101). El runtime no incluye Node, npm ni node_modules. El digest fija la base; la capa de actualización consume los parches disponibles de la misma rama Alpine. Renovar el digest/capa cuando Trivy informe nuevos CVEs; usar `--no-cache` para refrescar parches si se reutiliza una base.

Desde la raíz del repositorio:

```powershell
docker build -f frontend/Dockerfile -t datapulse-frontend:local frontend
# Backend ya ejecutándose en el host (Docker Desktop):
docker run --rm --name datapulse-frontend -p 127.0.0.1:8080:8080 -e BACKEND_URL=http://host.docker.internal:8000 datapulse-frontend:local
```

Abrir http://127.0.0.1:8080. En Linux se recomienda Compose; para apuntar al host, usar un origen/IP accesible desde el contenedor y una interfaz donde escuche la API. El runtime toma los resolvers de /etc/resolv.conf, por lo que no depende exclusivamente del DNS de una red Compose. El healthcheck comprueba los estáticos: la disponibilidad de la API es independiente.

Para levantar el stack Docker completo, configurar primero `.env` según el README raíz y liberar el puerto 8000 si se está usando el servidor local:

```powershell
docker compose up -d --build frontend
# En una base nueva, cargar los datos de demostración de forma explícita:
docker compose run --rm backend uv run --frozen --no-sync --no-dev python backend/manage.py seed_data
docker compose ps
```

Compose arranca db → backend saludable → frontend y publica el frontend en 127.0.0.1:8080 (`FRONTEND_PORT` permite cambiarlo). `BACKEND_URL=http://backend:8000` se resuelve dentro de Docker. El browser pide `/api/` en el mismo origen; no intenta resolver el hostname `backend`. Los servicios backend, db y test-postgresql conservan sus comandos y configuración previos. `docker compose down` conserva sus volúmenes; no usar `down -v` si se quieren mantener los datos.

### URL de API y CSP

Se eligió **build-time (opción A)**. `API_URL` genera `environment.prod.ts` solamente dentro del builder; el archivo del repositorio queda intacto. No se usa `--define` sobre una propiedad de objeto que Angular no reconoce como constante global. El output real es `dist/datapulse/browser`, y el build comprueba que exista su index. `CONFIGURATION` se fija a production para mantener AOT, hashes y CSP coherentes.

```powershell
docker build -f frontend/Dockerfile --build-arg API_URL=https://api.ejemplo.com/api/ -t datapulse-frontend:nube frontend
```

Cambiar la URL pública requiere reconstruir. El generador añade solo ese origen a `connect-src`; el backend debe permitir el origen del frontend mediante CORS. No introducir secretos en esos argumentos. La variable de runtime `BACKEND_URL` solo cambia el upstream interno del proxy para `/api/`; no reescribe el bundle ni constituye la opción B. La configuración Angular en runtime queda documentada como evolución, sin añadir código de aplicación en este alcance.

La [política de seguridad](../docs/SEGURIDAD_FRONTEND.md) detalla la CSP y cabeceras. La imagen sirve gzip, sin módulo Brotli de nginx. `index.html` y rutas SPA no se almacenan; archivos con hash son immutable por un año; assets sin hash duran una semana y favicon un día. Los errores/API no se cachean. El HTML generado se prepara para cargar CSS sin handlers inline, manteniendo `script-src 'self'`.

### Pipeline

`.github/workflows/frontend-ci.yml` tiene cuatro jobs: lint-and-check, test, build y docker-build. Usa setup-node v4 con Node 22.12.0 (mínimo soportado de esta rama), caché npm por el lockfile y `npm ci`. No cambia package.json ni incorpora uv. No existe un target ESLint: la comprobación estática utiliza los proyectos TypeScript estrictos existentes y la sintaxis de los scripts de infraestructura; no se simula un `ng lint` inexistente.

Se activa en push y PR hacia `feat/backend-datapulse` (rama predeterminada actual)
o `main`, cuando cambian frontend, su workflow, Compose, su política de seguridad
o `.gitattributes` (terminaciones LF de los scripts). También admite ejecución
manual mediante `workflow_dispatch`. Los filtros de PR se refieren a la rama de
destino, no a la rama de origen.

El job de imagen usa Buildx y caché gha, `push: false`, prueba HTTP contra un upstream efímero y escanea el runtime con Trivy 0.76.2, acción fijada al commit de v0.36.0. HIGH/CRITICAL hacen fallar el job, sin ignorar los no corregidos. Se conserva el reporte JSON como artifact. Solo hay permiso contents:read; no se publica nada en GHCR ni se solicitan credenciales de despliegue.

Los scripts `docker/upstream-fixture.mjs` y `docker/smoke-test.mjs` son verificaciones de infraestructura: rutas SPA, cabeceras, gzip, cache, 404, JWT/If-Match, cuerpo decimal, DELETE y PDF. La fixture queda fuera de la imagen final. No se añadió una suite E2E de Angular.

### Validación local de la entrega — 18/11/2026

- Builds con `/api/` y con `https://api.example.test/api/` correctos; URL absoluta presente en el bundle y su origen en la CSP.
- Runtime nginx UID 101, sin Node/npm/node_modules; nginx -t correcto y healthcheck healthy.
- Rutas SPA, 404 de assets, cabeceras, caché, gzip, proxy de JWT/If-Match/cuerpos, ETag, DELETE sin body y PDF: correctos.
- Docker standalone contra la API del host: HTTP 200. Stack Compose aislado: db/backend/frontend saludables; login, mapa de diez países y gráfica en navegador, sin errores de consola ni violaciones CSP. Paginación mantiene el puerto público en next.
- 5 pruebas de infraestructura y 25 Karma/Jasmine aprobadas; TypeScript estricto y actionlint 1.7.12 sin errores. Backend PostgreSQL: 61 pruebas aprobadas, sin skips.
- npm audit de producción: 0 vulnerabilidades. Trivy 0.76.2 del runtime parcheado: 0 HIGH / 0 CRITICAL; reporte local en `tmp/frontend-scan/trivy-frontend.json`.
- Pipeline validado localmente; no se ejecutó en GitHub ni se publicó imagen en GHCR. Se conservaron sin cambios los servicios previos y volúmenes del Compose raíz, además del código/configuración/pruebas Angular existentes.

Los entornos de verificación utilizan nombres y puertos separados. La ejecución habitual de desarrollo en 4200/8000 no se reemplaza por estos contenedores de prueba.
