# Preservación de evidencia (U3, señales U1 e incidentes U2)

Desde un shell Linux/WSL protegido, en la raíz del repo y con PG* configurado:

```sh
umask 077
stamp=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "evidencias/$stamp"
docker compose logs --no-color --timestamps backend db > "evidencias/$stamp/containers.log"
uv run python backend/manage.py verificar_auditoria > "evidencias/$stamp/verificacion.json"
uv run python backend/manage.py dumpdata core.LogActividad core.AuditHead --indent 2 > "evidencias/$stamp/auditoria.json"
pg_dump --format=custom --no-owner --no-privileges --file="evidencias/$stamp/database.dump"
backend_id=$(docker compose ps -q backend)
docker inspect "$backend_id" > "evidencias/$stamp/container-inspect.json"
# Solo para SQLite/archivos locales; PG vive en db. Inspect contiene entorno:
# tratar como secreto, nunca subir a repo/SIEM ni adjuntar sin redactar.
docker cp "$backend_id:/app/data" "evidencias/$stamp/data"
find "evidencias/$stamp" -type f ! -name SHA256SUMS ! -name MANIFEST.md -exec sha256sum {} \; > "evidencias/$stamp/SHA256SUMS"
sha256sum -c "evidencias/$stamp/SHA256SUMS"
```

Si verificar_auditoria falla, conservar igualmente su JSON y código de salida;
continuar adquisición como operaciones separadas (no `set -e` que aborte toda la
custodia). Para snapshot de archivos consistente, detener escritores o adquirir
snapshot forense. `docker pause "$backend_id"` preserva el contenedor en lugar
de destruirlo; no crea una imagen de memoria RAM ni garantiza flush de SQLite.
Nunca pausar DB antes de terminar un pg_dump lógico consistente.

Para un PDF sospechoso: `sha256sum informe.pdf` y `exiftool informe.pdf` sobre una
copia de trabajo. Metadatos no prueban autoría; comparar hash con export conocido.
Registrar hash de adquisición y antes/después de cada transferencia.

## Plantilla evidencias/{timestamp}/MANIFEST.md

```markdown
# Caso / identificador
- Adquirente y autorización:
- Inicio/fin UTC, reloj y desviación conocida:
- Sistema origen, container/image digest, commit:
- Método/herramientas/versiones y comandos:
- Archivos y SHA256: adjuntar SHA256SUMS
- Hash de SHA256SUMS anclado en ubicación independiente:
- Custodio, ubicación cifrada y controles de acceso:
- Transferencias: UTC / de / a / motivo / hash antes / hash después / firmas
- Acciones que alteraron el sistema y justificación:
- Limitaciones (volátil, ventana temporal, pérdidas conocidas):
```

Copiar solo a almacenamiento autorizado cifrado/inmutable; las claves van por
otro canal. No conservar dumps en repo; evidencias/ está ignorado. Un hash almacenado
junto al mismo archivo no protege contra un atacante que modifica ambos: anclar
el manifiesto externamente. Seguir [IR](IR.md) para cadena rota y [BCP](BCP.md) para continuidad.
