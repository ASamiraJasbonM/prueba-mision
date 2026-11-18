# Respuesta a incidentes (U2, con detección U1 y evidencia U3)

Marco: [NIST SP 800-61r3](https://csrc.nist.gov/pubs/sp/800/61/r3/final), integrado
con CSF 2.0: Govern/Identify/Protect preparan; Detect/Respond/Recover operan;
las lecciones mejoran el ciclo completo. Las fases de este runbook son operativas,
no una atribución del ciclo antiguo a R3.

| Actividad | Seguridad | Operaciones | Backend | Responsable negocio |
|---|---|---|---|---|
| Confirmar/registrar | A/R | C | C | I |
| Preservar/contener | A | R | C | I |
| Parche/revisión | A | C | R | I |
| Restaurar | C | R | C | A |
| Comunicación/postmortem | R | C | C | A |

R ejecuta, A aprueba/responde, C consulta, I informa. TODO asignar nombres/on-call.
Registrar UTC, alcance, decisiones, evidencia y responsable desde la primera señal.

## Token ADMIN filtrado

Detectar anomalías en auditoría/SIEM; preservar antes de contener. Invalidar todos
los refresh (terminal protegido; no imprimir tokens):

```sh
uv run python backend/manage.py shell -c "from rest_framework_simplejwt.token_blacklist.models import OutstandingToken,BlacklistedToken; [BlacklistedToken.objects.get_or_create(token=t) for t in OutstandingToken.objects.all()]"
```

Rotar **JWT_SIGNING_KEY** en gestor de secretos y reiniciar workers para invalidar
access y refresh firmados anteriormente. Si se usa SECRET_KEY como firma, rotarlo
con una nueva clave aleatoria (`uv run python -c 'from django.core.management.utils
import get_random_secret_key; print(get_random_secret_key())'` en terminal no
registrado); no mantener claves comprometidas en fallbacks. Conservar AUDIT_HMAC_KEY
y FIELD_ENCRYPTION_KEY: rotar SECRET_KEY no debe destruir evidencia/cifrado.
Restablecer contraseña afectada, revisar cambios de rol, enrolar/revalidar MFA.

## Brute-force sostenido

Confirmar ≥5 fallos/IP en 60 s en Grafana y LOGIN_BLOQUEADO; comprobar que no es
un proxy compartido. Mantener Axes; bloquear IP/rango en perímetro con vencimiento
y registro de aprobación. No desactivar CAPTCHA ni resetear contadores a ciegas.
Un caso legítimo confirmado puede desbloquearse con `uv run python
backend/manage.py axes_reset_ip <ip>` tras preservar evidencia. Verificar clientes
legítimos, revisar stuffing distribuido y añadir controles perimetrales.

## CVE crítico

Identificar versión e imagen por digest, evaluar exposición, aislar endpoint si
hay explotación. `uv lock --check`, export + pip-audit, parche mínimo con uv,
suite completa SQLite/PG, Bandit y Trivy. Reconstruir, desplegar digest revisado,
verificar health y errores; no ignorar aviso solo para liberar el pipeline.
Plazo HIGH/CRITICAL ≤7 días; si explotación activa, contención inmediata.

## Corrupción de auditoría

`uv run python backend/manage.py verificar_auditoria` produce JSON y exit1.
Detener escrituras/aislar, preservar [FORENSE](FORENSE.md), comparar cadena con
export/hash externos. No corregir la fila ni reseal automáticamente. Determinar
si fue compromiso de aplicación, rol DB o clave HMAC; restaurar una copia confiable
en entorno aislado según [RESTORE](RESTORE.md), verificar y aprobar reconciliación.

Tras recuperar: monitorizar errores/conflictos/logins, confirmar integridad con
negocio, comunicar alcance y acciones, postmortem sin culpas con fechas y dueños.
