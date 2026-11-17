# DataPulse Latam — backend

Implementación por etapas de Django + DRF. Frontend reservado; sin despliegue remoto en este encargo.

## Desarrollo local (PowerShell, Python 3.12)

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Sustituir SECRET_KEY en .env por un secreto aleatorio local.
.\.venv\Scripts\python backend/manage.py check
```

La configuración lee `.env` desde la raíz. `SECRET_KEY` es obligatorio. SQLite local; PostgreSQL mediante `DATABASE_URL`. `DEBUG=False` activa cookies seguras y redirección HTTPS salvo ajuste explícito para un proxy de desarrollo.

## Estado

Evidencia por etapa en `docs/ETAPAS.md`. El prompt backend del usuario tiene prioridad sobre decisiones recomendadas de `PLAN_CORREGIDO.md`.


- Etapa 00: Bootstrap, health y OpenAPI base

- Etapa 01: Usuario custom con login por email y administrador demo

- Etapa 01: Verificacion efectiva de usuarios desde directorio backend
