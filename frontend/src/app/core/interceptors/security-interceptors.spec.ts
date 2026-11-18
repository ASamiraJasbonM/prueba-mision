import { TestBed } from '@angular/core/testing';
import { HttpClient, HttpErrorResponse, HttpHeaders, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { AuthService } from '../auth/auth.service';
import { jwtInterceptor } from './jwt.interceptor';
import { errorInterceptor } from './error.interceptor';
import { NotificationService } from '../state/notification.service';
import { errorMessage, retryAfterSeconds } from '../http/error-parser';

describe('Errores y frontera JWT de seguridad', () => {
  let http: HttpClient;
  let controller: HttpTestingController;
  let auth: AuthService;
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ providers: [provideRouter([]),
      provideHttpClient(withInterceptors([errorInterceptor, jwtInterceptor])), provideHttpClientTesting(),
      { provide: NotificationService, useValue: { show: () => undefined } }] });
    http = TestBed.inject(HttpClient);
    controller = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(AuthService);
    spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
  });
  afterEach(() => { controller.verify(); localStorage.clear(); });
  it('no filtra secretos ni details en errores 500', () => {
    const error = new HttpErrorResponse({ status: 500, error: { error: {
      message: 'secret-token', details: { traceback: 'database-password' } } } });
    expect(errorMessage(error)).not.toContain('secret-token');
    expect(errorMessage(error)).not.toContain('database-password');
  });
  it('interpreta Retry-After en segundos y fecha HTTP', () => {
    const error = new HttpErrorResponse({ status: 429, headers: new HttpHeaders({ 'Retry-After': '900' }) });
    expect(retryAfterSeconds(error)).toBe(900);
    expect(errorMessage(error)).toContain('900 segundos');
    expect(retryAfterSeconds(new HttpErrorResponse({ status: 429,
      headers: new HttpHeaders({ 'Retry-After': 'Wed, 18 Nov 2026 20:00:30 GMT' }) }), Date.parse('2026-11-18T20:00:00Z'))).toBe(30);
  });
  it('CAPTCHA y MFA públicos no llevan JWT y un MFA inválido no borra otra sesión', () => {
    auth.setTokens({ access: 'access', refresh: 'refresh' });
    http.get('/api/auth/captcha/').subscribe();
    const captcha = controller.expectOne('/api/auth/captcha/');
    expect(captcha.request.headers.has('Authorization')).toBeFalse();
    captcha.flush({});
    http.post('/api/auth/mfa/verify-login/', {}).subscribe({ error: () => undefined });
    const mfa = controller.expectOne('/api/auth/mfa/verify-login/');
    expect(mfa.request.headers.has('Authorization')).toBeFalse();
    mfa.flush({}, { status: 401, statusText: 'Unauthorized' });
    expect(auth.accessToken).toBe('access');
  });
  it('no retira JWT de los endpoints protegidos de autenticación', () => {
    auth.setTokens({ access: 'access', refresh: 'refresh' });
    http.post('/api/auth/mfa/enroll/', {}).subscribe();
    const enroll = controller.expectOne('/api/auth/mfa/enroll/');
    expect(enroll.request.headers.get('Authorization')).toBe('Bearer access');
    enroll.flush({});
  });
  it('no reintenta un segundo 401 después de renovar', () => {
    auth.setTokens({ access: 'old', refresh: 'refresh' });
    http.get('/api/paises/').subscribe({ error: () => undefined });
    controller.expectOne('/api/paises/').flush({}, { status: 401, statusText: 'Unauthorized' });
    controller.expectOne('/api/auth/refresh/').flush({ access: 'new' });
    controller.expectOne('/api/paises/').flush({}, { status: 401, statusText: 'Unauthorized' });
    controller.expectNone('/api/auth/refresh/');
    expect(auth.accessToken).toBeNull();
  });
});
