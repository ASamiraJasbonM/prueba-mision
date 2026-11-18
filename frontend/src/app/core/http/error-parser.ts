import { HttpErrorResponse } from '@angular/common/http';
export function errorMessage(error: unknown): string {
  if (!(error instanceof HttpErrorResponse)) return 'No se pudo completar la operación.';
  if (error.status === 0) return 'Sin conexión con el servidor. Revisa la red e intenta de nuevo.';
  const body = error.error as { error?: { message?: string; details?: unknown } } | null;
  const flatten = (value: unknown): string[] =>
    typeof value === 'string'
      ? [value]
      : Array.isArray(value)
        ? value.flatMap(flatten)
        : value && typeof value === 'object'
          ? Object.values(value).flatMap(flatten)
          : [];
  const details = flatten(body?.error?.details).slice(0, 3).join(' ');
  const statuses: Record<number, string> = {
    401: 'Tu sesión venció. Inicia sesión de nuevo.',
    403: 'No tienes permisos para esta acción.',
    404: 'No se encontró el recurso.',
    409: 'El portafolio cambió. Revisa los datos actualizados antes de reintentar.',
    429: 'Demasiadas solicitudes. Espera un momento antes de intentar de nuevo.',
  };
  return (
    details ||
    body?.error?.message ||
    statuses[error.status] ||
    'No se pudo completar la operación.'
  );
}
