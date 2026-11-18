import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { AuthService } from './auth.service';

describe('Integridad de sesión y MFA', () => {
  let auth: AuthService;
  let http: HttpTestingController;
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    auth = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => { http.verify(); localStorage.clear(); });
  it('persiste ambas claves explícitas y limpia ambas al salir', () => {
    auth.setTokens({ access: 'access', refresh: 'refresh' });
    expect(localStorage.getItem('datapulse.auth.access')).toBe('access');
    expect(localStorage.getItem('datapulse.auth.refresh')).toBe('refresh');
    auth.logout('manual');
    expect(localStorage.getItem('datapulse.auth.access')).toBeNull();
    expect(localStorage.getItem('datapulse.auth.refresh')).toBeNull();
  });
  it('un logout remoto invalida el refresh en vuelo sin escribir de nuevo en storage', () => {
    auth.setTokens({ access: 'old', refresh: 'refresh' });
    auth.refresh().subscribe({ error: () => undefined });
    const pending = http.expectOne('/api/auth/refresh/');
    localStorage.removeItem('datapulse.auth.access');
    const remove = spyOn(localStorage, 'removeItem').and.callThrough();
    window.dispatchEvent(new StorageEvent('storage', { key: 'datapulse.auth.access', newValue: null }));
    pending.flush({ access: 'late' });
    expect(auth.accessToken).toBeNull();
    expect(auth.user).toBeNull();
    expect(remove).not.toHaveBeenCalled();
  });
  it('conserva los tokens ante indisponibilidad temporal del perfil', () => {
    auth.setTokens({ access: 'access', refresh: 'refresh' });
    auth.restore().subscribe();
    http.expectOne('/api/auth/me/').flush({}, { status: 503, statusText: 'Unavailable' });
    expect(auth.accessToken).toBe('access');
    expect(auth.user).toBeNull();
  });
  it('un reto MFA no almacena tokens y verifica con el contrato real code', () => {
    auth.login('admin@test.com', 'password').subscribe();
    http.expectOne('/api/auth/login/').flush({ mfa_required: true, mfa_token: 'ephemeral' });
    expect(auth.accessToken).toBeNull();
    expect(localStorage.getItem('datapulse.auth.access')).toBeNull();
    auth.verifyMfa('123456').subscribe();
    const verify = http.expectOne('/api/auth/mfa/verify-login/');
    expect(verify.request.body).toEqual({ mfa_token: 'ephemeral', code: '123456' });
    verify.flush({ access: 'access', refresh: 'refresh' });
    http.expectOne('/api/auth/me/').flush({ id: 1, rol: 'ADMIN' });
    expect(auth.hasRole('ADMIN')).toBeTrue();
    expect(JSON.stringify(localStorage)).not.toContain('ephemeral');
  });
  it('no revive una verificación MFA tardía tras logout', () => {
    auth.login('admin@test.com', 'password').subscribe();
    http.expectOne('/api/auth/login/').flush({ mfa_required: true, mfa_token: 'ephemeral' });
    auth.verifyMfa('123456').subscribe({ error: () => undefined });
    const pending = http.expectOne('/api/auth/mfa/verify-login/');
    auth.logout();
    pending.flush({ access: 'late', refresh: 'late-refresh' });
    expect(auth.accessToken).toBeNull();
  });
  it('rechaza una respuesta que no contiene ni JWT ni reto MFA válido', () => {
    auth.login('admin@test.com', 'password').subscribe({ error: () => undefined });
    http.expectOne('/api/auth/login/').flush({ mfa_required: true });
    expect(auth.accessToken).toBeNull();
  });
  it('actualiza permisos exclusivamente al volver a consultar me', () => {
    auth.login('admin@test.com', 'password').subscribe();
    http.expectOne('/api/auth/login/').flush({ access: 'access', refresh: 'refresh' });
    http.expectOne('/api/auth/me/').flush({ id: 1, rol: 'ADMIN' });
    auth.reloadProfile().subscribe();
    http.expectOne('/api/auth/me/').flush({ id: 1, rol: 'VIEWER' });
    expect(auth.hasRole('ADMIN')).toBeFalse();
    expect(auth.canWrite()).toBeFalse();
  });
});
