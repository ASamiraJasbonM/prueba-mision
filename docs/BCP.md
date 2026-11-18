# Continuidad del negocio (U3; coordinación U1/U2)

Objetivos propuestos: RTO 4 horas, RPO 24 horas. Verificación: backup diario,
restauración trimestral aislada con medición de `scripts/restore.sh`, comparar
timestamp del último backup y último evento confirmado. No son SLA aprobados.
Roles son responsabilidades por asignar a personas antes del despliegue.

| Riesgo adaptado a DataPulse | Impacto | Mitigación | Responsable |
|---|---|---|---|
| PostgreSQL caído | API no disponible/escrituras detenidas | Snapshot/dump cifrado y restore validado | Operaciones |
| Proveedor externo caído | Indicadores antiguos | Conservar última versión, alertar sync_error, reintentar controlado | Backend |
| Fuga credenciales/tokens | Acceso indebido | Rotar JWT, bloquear refresh, MFA, investigar auditoría | Seguridad |
| Dependencia vulnerable | Explotación/DoS | CI SCA/SAST/Trivy, parches ≤7 días HIGH/CRITICAL | Backend/DevOps |
| Ransomware | Pérdida de datos y servicio | Copia fuera de host, cifrado, separación de claves, ensayo aislado | Operaciones |
| Pérdida/manipulación logs | Evidencia incompleta | HMAC, cadena, export periódico con hash externo y almacenamiento inmutable | Seguridad |

Tabla basada en los riesgos enumerados en el encargo. TODO contrastar fila por
fila con Tabla 5 del PDF U3, que no se adjuntó. U1 aporta detección/SIEM; U2
priorización de CVEs y respuesta. Ver [IR](IR.md), [SIEM](SIEM.md), [RESTORE](RESTORE.md).

El ensayo local de RESTORE registra duración real en ese documento. No incluye
detección, aprobación, aprovisionamiento, DNS/TLS ni millones de filas: reservar
el resto de la ventana RTO y ensayar volumen representativo.
