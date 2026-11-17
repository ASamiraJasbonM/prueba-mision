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

## Etapa 04: verificada

Autenticacion JWT, perfiles y permisos seguros

Evidencia completa: [etapas/04.md](etapas/04.md).

## Etapa 05: verificada

Paises, indicadores y sincronizacion idempotente con Decimal

Evidencia completa: [etapas/05.md](etapas/05.md).

## Etapa 06: verificada

IRPC Decimal, alertas y lectura individual

Evidencia completa: [etapas/06.md](etapas/06.md).

## Etapa 07: verificada

Portafolios transaccionales, posiciones y exportacion PDF

Evidencia completa: [etapas/07.md](etapas/07.md).

## Etapa 08: verificada

Dashboard con KPIs, mapa y tendencias de cinco anios

Evidencia completa: [etapas/08.md](etapas/08.md).

## Etapa 09: verificada

Logs JSON, auditoria y comandos programables encadenados

Evidencia completa: [etapas/09.md](etapas/09.md).

## Etapa 10: verificada

Seed completo, regresiones, OpenAPI y documentacion final

Evidencia completa: [etapas/10.md](etapas/10.md).

## Observación P1

Regla canonica de redondeo y bordes de clasificacion

Verificación y salida completa: [observaciones/P1.md](observaciones/P1.md).

## Observación P2

Trazabilidad comprobada de los escenarios IRPC 69, 75 y 72

Verificación y salida completa: [observaciones/P2.md](observaciones/P2.md).

## Observación P3

Factores negativos explicitos y detalle trazable del IRPC

Verificación y salida completa: [observaciones/P3.md](observaciones/P3.md).
