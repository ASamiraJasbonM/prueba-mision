# Pruebas de navegador con backend real

Requisitos: Python 3.12, uv 0.13.9 y Node 22.12+ de la rama 22. Desde la raíz:

```powershell
uv sync --frozen
cd frontend
npm ci
npx playwright install chromium
npm run build:e2e
npm run test:e2e
```

En Linux CI se instala Chromium con `npx playwright install --with-deps chromium`.
Playwright 1.65.1 queda fijado en package.json y package-lock.json. Si el intérprete
está fuera de `.venv`, definir E2E_PYTHON con su ruta antes de ejecutar las pruebas.

## Qué se prueba

Seis casos: tres flujos en Chromium a 1920×1080 y a 768×1024:

1. Login ANALISTA, navegación, alta de portafolio, monto inválido bloqueado,
   alta/edición de posición con decimales exactos, PDF real y borrado confirmado.
2. Edición concurrente autorizada por otro usuario, 409, relectura de la versión
   vigente y reenvío explícito después de revisar. No hay reintento ciego.
3. VIEWER sin controles de escritura, ruta protegida y 403 del servidor; detalle
   de país con bandera local cargada, gráficos y ausencia de desborde horizontal.

No hay mocks de respuestas API: navega la SPA compilada de producción y llama a
Django real. La simulación de concurrencia realiza una segunda escritura auténtica
con la API de ADMIN mientras el formulario conserva su versión anterior.

## Aislamiento

Playwright arranca `scripts/e2e_server.py` en 127.0.0.1:18120. El proceso crea claves
aleatorias y SQLite temporal, aplica migraciones y seed, y sirve estáticos y API
en el mismo origen con la CSP de producción. No toma conexión ni claves de .env/Render,
no consulta proveedores, no permite un BASE_URL remoto y no reutiliza un servidor
existente. Las instancias normales 4200/8000 y la base demo no se tocan.

Solo la fixture efímera usa caché en memoria, desactiva CAPTCHA y amplía throttling para ejecutar el
recorrido de negocio sin retos humanos ni cuotas entre casos. Los controles de
CAPTCHA, MFA y throttling de producción conservan sus regresiones independientes.
El build E2E restaura environment.prod.ts al terminar y no cambia la URL de Pages.

Resultados y capturas quedan en frontend/test-results y frontend/playwright-report,
ignorados por Git. Las trazas de fallo contienen únicamente la sesión demo efímera.
CI conserva estos artifacts siete días y bloquea la publicación de Pages si falla
el job e2e; no se rebajan los gates existentes de Karma, Docker ni Trivy.
