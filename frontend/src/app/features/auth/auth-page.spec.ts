import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ActivatedRoute, convertToParamMap, provideRouter, Router } from '@angular/router';
import { AuthPage } from './auth-page';
import { AuthService } from '../../core/auth/auth.service';

describe('Login reforzado con CAPTCHA/MFA', () => {
  let fixture: ComponentFixture<AuthPage>;
  let page: AuthPage;
  let http: HttpTestingController;
  let router: Router;
  const key = 'a'.repeat(40);
  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({ imports: [AuthPage], providers: [provideRouter([]),
      provideHttpClient(), provideHttpClientTesting(),
      { provide: ActivatedRoute, useValue: { snapshot: { data: {}, queryParamMap: convertToParamMap({}) } } }
    ] }).compileComponents();
    fixture = TestBed.createComponent(AuthPage);
    page = fixture.componentInstance;
    http = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    spyOn(router, 'navigateByUrl').and.resolveTo(true);
    page.form.patchValue({ email: 'admin@test.com', password: 'Strong-test-2026!' });
    fixture.detectChanges();
  });
  afterEach(() => { http.verify(); localStorage.clear(); });
  it('muestra el CAPTCHA requerido y reintenta con clave y respuesta', () => {
    page.submit();
    http.expectOne('/api/auth/login/').flush({ error: { code: 'captcha_required' } }, { status: 400, statusText: 'Bad Request' });
    http.expectOne('/api/auth/captcha/').flush({ captcha_key: key, image_url: `/api/auth/captcha-image/image/${key}/` });
    http.expectOne(`${location.origin}/api/auth/captcha-image/image/${key}/`).flush(new Blob(['PNG'], { type: 'image/png' }));
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('img').src).toMatch(/^blob:/);
    page.form.controls.captcha_answer.setValue('answer');
    page.submit();
    const login = http.expectOne('/api/auth/login/');
    expect(login.request.body.captcha_key).toBe(key);
    expect(login.request.body.captcha_answer).toBe('answer');
    login.flush({ access: 'access', refresh: 'refresh' });
    http.expectOne('/api/auth/me/').flush({ id: 1, rol: 'ADMIN' });
    expect(router.navigateByUrl).toHaveBeenCalledWith('/dashboard');
  });
  it('presenta MFA sin guardar el reto y completa autenticación mediante recovery', () => {
    page.submit();
    http.expectOne('/api/auth/login/').flush({ mfa_required: true, mfa_token: 'temporary' });
    fixture.detectChanges();
    expect(page.mfaRequired()).toBeTrue();
    expect(TestBed.inject(AuthService).accessToken).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Verificar identidad');
    expect(page.form.controls.password.value).toBe('');
    page.mfaForm.controls.code.setValue('b'.repeat(32));
    page.submitMfa();
    const verify = http.expectOne('/api/auth/mfa/verify-login/');
    expect(verify.request.body).toEqual({ mfa_token: 'temporary', code: 'b'.repeat(32) });
    verify.flush({ access: 'access', refresh: 'refresh' });
    http.expectOne('/api/auth/me/').flush({ id: 1, rol: 'ADMIN' });
    expect(router.navigateByUrl).toHaveBeenCalledWith('/dashboard');
    expect(page.mfaForm.controls.code.value).toBe('');
  });
  it('respeta Retry-After sin reenviar credenciales durante el bloqueo', fakeAsync(() => {
    page.submit();
    http.expectOne('/api/auth/login/').flush({}, { status: 429, statusText: 'Too Many Requests', headers: { 'Retry-After': '30' } });
    page.submit();
    http.expectNone('/api/auth/login/');
    expect(page.retrySeconds()).toBe(30);
    tick(30000);
    expect(page.retrySeconds()).toBe(0);
  }));
  it('rechaza imágenes CAPTCHA externas o esquemas ejecutables', () => {
    page.loadCaptcha();
    http.expectOne('/api/auth/captcha/').flush({ captcha_key: key, image_url: 'https://evil.test/steal' });
    expect(page.captchaImage()).toBe('');
    page.loadCaptcha();
    http.expectOne('/api/auth/captcha/').flush({ captcha_key: key, image_url: 'javascript:alert(1)' });
    expect(page.captchaImage()).toBe('');
  });
  it('no repite el registro si el login posterior exige otro CAPTCHA', () => {
    fixture.destroy();
    TestBed.inject(ActivatedRoute).snapshot.data['register'] = true;
    fixture = TestBed.createComponent(AuthPage);
    page = fixture.componentInstance;
    page.form.patchValue({ nombre_completo: 'Nuevo', email: 'new@test.com', password: 'Strong-test-2026!' });
    page.submit();
    http.expectOne('/api/auth/register/').flush({ error: { code: 'captcha_required' } }, { status: 400, statusText: 'Bad Request' });
    http.expectOne('/api/auth/captcha/').flush({ captcha_key: key, image_url: `/api/auth/captcha-image/image/${key}/` });
    http.expectOne(`${location.origin}/api/auth/captcha-image/image/${key}/`).flush(new Blob(['PNG'], { type: 'image/png' }));
    page.form.controls.captcha_answer.setValue('first');
    page.submit();
    http.expectOne('/api/auth/register/').flush({ id: 7, rol: 'ANALISTA' });
    http.expectOne('/api/auth/login/').flush({ error: { code: 'captcha_required' } }, { status: 400, statusText: 'Bad Request' });
    http.expectOne('/api/auth/captcha/').flush({ captcha_key: key, image_url: `/api/auth/captcha-image/image/${key}/` });
    http.expectOne(`${location.origin}/api/auth/captcha-image/image/${key}/`).flush(new Blob(['PNG'], { type: 'image/png' }));
    page.form.controls.captcha_answer.setValue('second');
    page.submit();
    http.expectNone('/api/auth/register/');
    http.expectOne('/api/auth/login/').flush({ access: 'access', refresh: 'refresh' });
    http.expectOne('/api/auth/me/').flush({ id: 7, rol: 'ANALISTA' });
    expect(router.navigateByUrl).toHaveBeenCalledWith('/dashboard');
  });
});
