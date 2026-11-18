# SIEM local: Loki, Grafana y Alloy (U1, enlace U2/U3)

Loki almacena/consulta, Alloy recolecta, Grafana correlaciona/visualiza. Promtail
terminó soporte el 2 de marzo de 2026; se usa su sucesor mantenido según
[Grafana](https://grafana.com/docs/grafana-cloud/send-data/alloy/set-up/migrate/from-promtail/).
Versiones fijadas: Loki 3.6.20, Grafana 13.3.1, Alloy 1.21.3. No Wazuh ni socket
Docker dentro de un contenedor. Puertos solo loopback; Loki sin autenticación
es exclusivamente local, no publicarlo. Volúmenes separados del compose principal.

```powershell
# Raíz del repositorio, contraseña desde gestor de secretos/entorno, no repo.
New-Item -ItemType Directory -Force tmp/siem | Out-Null
$env:GRAFANA_ADMIN_PASSWORD = '<clave-local-no-versionada>'
docker compose -f docker-compose.siem.yaml --profile siem up -d
# En otra terminal, mientras backend/db del compose principal están activos:
powershell -File scripts/siem_logs.ps1
# Validación del provisioning, consultas e ingestión:
uv run python scripts/verify_siem.py
```

Abrir http://127.0.0.1:13000 y entrar con admin/clave configurada. Dashboard
DataPulse / DataPulse Security; datasource Loki y cinco reglas se importan
automáticamente. Cambiar la variable después de inicializar el volumen no rota
la contraseña existente: usar administración de Grafana. Evitar Out-File con
buffering largo para investigación en tiempo real; verificar latencia del
colector en la plataforma. Alternativa Linux:

```sh
mkdir -p tmp/siem
docker compose logs --follow --no-color --no-log-prefix backend db >> tmp/siem/services.log
```

Logs JSON backend se parsean; DB puede emitir texto, conservado como tal. No se
extraen contraseñas, Authorization, tokens ni cuerpos. Archivo ignorado tmp/;
limitar permisos, rotar archivo y eliminar por retención aprobada. Retención Loki
7 días local; producción requiere almacenamiento externo cifrado, backups,
límites de cardinalidad y acceso autenticado. No es evidencia inmutable.

| Panel | Ventana/campo |
|---|---|
| Top IPs login401 | 15 min, ip/path/status |
| 5xx por endpoint | 60 min, path/status |
| p95 duración | 60 min, duracion_ms/path |
| sync_error país/operación | 60 min, pais/operacion |

| Regla | Condición |
|---|---|
| brute_force_login | ≥5 login401 por IP en 60 s; usuario anónimo no tiene usuario_id |
| privilege_escalation_attempt | Evento explícito al rechazar campos de privilegio en perfil/registro; no registrar body |
| mass_conflict | ≥10 conflictos409 por usuario en 5 min |
| error_5xx_burst | Más de 5% respuestas5xx/total en 5 min |
| audit_chain_broken | Evento audit_verification ok=false en 5 min |

`ops/grafana/rules.yaml` contiene expresiones y umbrales. Evaluación cada minuto,
sin contención automática. TODO configurar contact point/on-call y alertas por
falta de ingestión/verificación; sin invocar verificar_auditoria periódicamente,
la regla no puede detectar una cadena rota por sí sola. Programar comando con
salida JSON al mismo flujo, por ejemplo cada 15 minutos en el scheduler existente.

`uv run python scripts/build_siem_config.py` regenera dashboard y reglas versionados;
`verify_siem.py` verifica 4 paneles, 5 reglas, las 9 consultas contra Loki y muestra
conteo de muestra de datos. Ensayo usó 228 eventos reales JSON de la suite/seed,
con muestra de 100 consultada; no se simularon incidentes en producción.

Relacionar el instante/IP/usuario de un evento con LogActividad; preservar export,
dump y hash externo según [FORENSE](FORENSE.md) (U3). Un alertamiento inicia el
runbook [IR](IR.md) (U2), no prueba por sí solo compromiso. [SEGURIDAD §5](SEGURIDAD.md#5-siem-u1).
