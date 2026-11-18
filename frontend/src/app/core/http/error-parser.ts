import { HttpErrorResponse } from '@angular/common/http';
export function errorCode(error: unknown): string | null {
  if (!(error instanceof HttpErrorResponse)) return null;
  const body: unknown = error.error;
  if (!body || typeof body !== 'object' || !('error' in body)) return null;
  const envelope = body.error;
  return envelope && typeof envelope === 'object' && 'code' in envelope && typeof envelope.code === 'string'
    ? envelope.code : null;
}
export function retryAfterSeconds(error: unknown, now = Date.now()): number {
  if (!(error instanceof HttpErrorResponse)) return 0;
  const value = error.headers.get('Retry-After');
  if (!value) return 0;
  const seconds = /^\d+$/.test(value) ? Number(value) : Math.ceil((Date.parse(value) - now) / 1000);
  return Number.isFinite(seconds) ? Math.max(0, Math.ceil(seconds)) : 0;
}
export function publicAuthRequest(url: string): boolean {
  return /\/auth\/(?:login|register|refresh|captcha|captcha-image(?:\/.*)?|mfa\/verify-login)\/$/.test(new URL(url, location.origin).pathname);
}
export function errorMessage(error: unknown): string {
  if (!(error instanceof HttpErrorResponse)) return 'No se pudo completar la operación.';
  if (error.status === 0) return 'Sin conexión con el servidor. Revisa la red e intenta de nuevo.';
  if (error.status >= 500) return 'El servidor no pudo completar la operación. Intenta más tarde o contacta soporte.';
  const code = errorCode(error);
  if (code === 'captcha_required' || code === 'captcha_invalid') return 'Completa el reto de verificación para continuar.';
  const body = error.error as { error?: { message?: unknown } } | null;
  const statuses: Record<number, string> = {
    401: 'Tu sesión venció. Inicia sesión de nuevo.',
    403: 'No tienes permisos para esta acción.',
    404: 'No se encontró el recurso.',
    409: 'El portafolio cambió. Revisa los datos actualizados antes de reintentar.',
    429: 'Demasiadas solicitudes. Espera un momento antes de intentar de nuevo.',
  };
  if (error.status === 429) {
    const seconds = retryAfterSeconds(error);
    return seconds ? `Demasiadas solicitudes. Intenta de nuevo en ${seconds} segundos.` : statuses[429];
  }
  const message = body?.error?.message;
  // Never expose details, stack traces or token-bearing bodies, even in logs.
  if ([400, 409].includes(error.status) && typeof message === 'string' && message.trim()) return message.slice(0, 240);
  return statuses[error.status] ?? 'No se pudo completar la operación.';
}
