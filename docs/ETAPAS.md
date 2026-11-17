# Registro de ejecución por etapas

## Decisiones iniciales

- Etapa 0 necesita un proyecto Django importable: se crea configuración base aquí; etapa 1 añade usuario custom antes de ejecutar cualquier migración.
- DRF/OpenAPI se configuran desde bootstrap, completando sus políticas en etapa 3.
- La regla transversal de precisión prevalece sobre la frase contradictoria de etapa 6: umbrales con valores crudos, compuesto cuantizado HALF_UP a dos decimales antes de clasificar.
- Repositorio nuevo en rama `feat/backend-datapulse`; sin push ni despliegue remoto.
- La creación estándar del venv falló en ensurepip; se usa pip del intérprete anfitrión con `--python` apuntando al venv. Las instalaciones solo afectan `.venv`.

## Etapa 00: verificada

Bootstrap, health y OpenAPI base

Evidencia completa: [etapas/00.md](etapas/00.md).

## Etapa 01: verificada

Usuario custom con login por email y administrador demo

Evidencia completa: [etapas/01.md](etapas/01.md).

## Etapa 01: verificada

Verificacion efectiva de usuarios desde directorio backend

Evidencia completa: [etapas/01.md](etapas/01.md).

## Etapa 02: verificada

Modelo relacional completo, constraints e indices

Evidencia completa: [etapas/02.md](etapas/02.md).

## Etapa 03: verificada

Politicas DRF, errores uniformes y throttling

Evidencia completa: [etapas/03.md](etapas/03.md).
