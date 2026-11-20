# Gestión de dependencias con uv

La fuente de dependencias activa es `pyproject.toml` + `uv.lock`. Se elimina `requirements.txt` para impedir dos instalaciones divergentes; el histórico queda en Git y en los informes antiguos, no como archivo de instalación alternativo.

## Versiones y grupos

- Python `>=3.12,<3.13` y `.python-version=3.12`: mismo minor que el backend validado, sin abrir soporte a 3.13.
- uv 0.13.9 en Docker y GitHub Actions. Los resultados de la migración inicial a uv 0.10.11 que aparecen abajo son históricos.
- Dependencias de producción y restricciones transitivas en `pyproject.toml`; el lock conserva versiones y hashes exactos, incluidos los controles de seguridad incorporados después del bootstrap.
- Django/unittest proporcionan el runner. El grupo `dev` contiene Bandit y pip-audit; Docker y el servidor E2E solo necesitan las dependencias de producción.
- `package=false`: el backend no se empaqueta ni se instala editable. `compile-bytecode=true` prepara bytecode de las dependencias.

## Reproducir y actualizar

```powershell
uv lock --check
uv sync --frozen
uv run --frozen python backend/manage.py check
uv run --frozen python backend/manage.py makemigrations --check --dry-run
uv run --frozen python backend/manage.py test -v 2
uv run --frozen python backend/manage.py spectacular --validate --fail-on-warn --file docs/openapi.yaml
uv run --frozen python scripts/check_numeric_policy.py
uv pip list --format json
```

`uv pip list` solo inspecciona el entorno; no invoca pip ni instala paquetes. Para un cambio deliberado se edita el pin correspondiente, se ejecuta `uv lock`, se revisa el diff y se vuelve a verificar. `--frozen` instala el lock sin resolver versiones nuevas; CI también ejecuta `uv lock --check` para detectar un manifiesto desincronizado.

La comparación inicial en Windows reproduce los 30 pins del archivo anterior sin cambiar versiones. El venv Windows previo no tenía Gunicorn: `uv sync --frozen` lo añade exactamente en 27.0.1, ya presente en la imagen Linux anterior. `tzdata==2026.6` permanece bloqueado como dependencia de Django para Windows; en Linux no es necesario y uv respeta ese marcador. El antiguo requirements instalaba ese paquete también en Linux aunque no se utilizara. Las demás versiones se conservan; el nuevo venv de uv tampoco contiene el pip de bootstrap del venv antiguo.

## Docker y Compose

El builder copia primero manifiesto, lock y versión de Python y ejecuta `uv sync --frozen --no-dev --no-build`, usando una caché de uv y wheels. La imagen final copia `/opt/venv` y el binario uv, conserva appuser, healthcheck y Gunicorn, y no sincroniza dependencias al arrancar.

Compose ejecuta `uv run --frozen --no-sync --no-dev` para migraciones y pruebas. `--no-sync` usa el entorno ya construido, sin instalaciones ni escrituras sobre el venv de producción. La normalización de SQLite a `/app/data/db.sqlite3`, sus volúmenes y el servicio PostgreSQL no cambian.

```powershell
docker compose up -d db
docker compose up --build -d backend
docker compose run --rm backend uv run --frozen --no-sync --no-dev python backend/manage.py test -v 2
docker compose --profile test run --rm test-postgresql
docker build -t datapulse-backend .
docker run --rm datapulse-backend whoami
docker run --rm --env-file .env datapulse-backend uv run --frozen --no-sync --no-dev python backend/manage.py check
```

En `.env` se requiere POSTGRES_PASSWORD; si 5432 está reservado se puede usar POSTGRES_PORT=15432. Para usar PostgreSQL en el backend su URL debe apuntar al host `db`. La imagen de producción no ejecuta migraciones, collectstatic ni seed en CMD.

## CI

Se conservan los cuatro jobs. `setup-uv` instala la versión fijada y cachea por `uv.lock`; se retira la caché pip y todo `pip install`. Cada job Python comprueba el lock, sincroniza con `--frozen` y ejecuta mediante `uv run --frozen`. Se conserva DEBUG=False y SECURE_SSL_REDIRECT=False para HTTP en tests, así como el rechazo de omisiones en PostgreSQL. El build mantiene caché Buildx, `push:false` y comprobación appuser/importación.

Referencias oficiales: [lock y sincronización](https://docs.astral.sh/uv/concepts/projects/sync/), [Docker](https://docs.astral.sh/uv/guides/integration/docker/), [GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/).

## Validación de la migración

| Comprobación ejecutada | Resultado |
|---|---|
| `uv lock` y `uv lock --check` con Python 3.12 | Resolución de 31 entradas: proyecto virtual y 30 paquetes; lock vigente |
| `uv sync --frozen` y repetición offline | Entorno reproducido; ninguna versión previa cambia |
| Inventario Windows antes/después con `uv pip list --format json` | 30 pins iguales al archivo de referencia; solo se incorpora Gunicorn ausente del antiguo venv Windows |
| Inventario Linux antes/después | 29 versiones de producción iguales; se omiten pip de bootstrap y tzdata condicionado a Windows |
| Check, deriva de migraciones, OpenAPI y política numérica mediante uv antes de editar Docker/CI | Todos exit 0; sin cambios de esquema ni advertencias OpenAPI |
| Suite local mediante uv | 61 pruebas, 59 aprobadas y 2 omitidas de PostgreSQL |
| Build multi-stage con `uv sync --frozen --no-dev --no-build` | Correcto; usuario appuser y uv 0.10.11 |
| Suite Docker SQLite con DEBUG=False y redirección desactivada | 61 pruebas, 59 aprobadas y 2 omitidas |
| Suite Docker PostgreSQL mediante uv | 61 aprobadas, ninguna omitida |
| Healthcheck con DEBUG=False, redirección activa y dominio no localhost | Healthy |
| Workflow migrado | actionlint sin errores; caché uv y ninguna instalación con pip |

Código de negocio, migraciones, pruebas y settings permanecen intactos. Las ejecuciones Docker usan un proyecto temporal aislado y credenciales dummy. No se ejecutó el workflow en GitHub: el repositorio local no tiene remoto configurado.
