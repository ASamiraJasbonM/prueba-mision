import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { AuthService } from './auth.service';

describe('AuthService', () => {
  let auth: AuthService;
  let http: HttpTestingController;
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    auth = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => {
    http.verify();
    localStorage.clear();
  });
  it('obtiene el perfil del servidor antes de conceder permisos', () => {
    auth.login('analista@test.com', 'secret').subscribe();
    http.expectOne('/api/auth/login/').flush({ access: 'access', refresh: 'refresh' });
    expect(auth.user).toBeNull();
    http.expectOne('/api/auth/me/').flush({
      id: 2,
      email: 'analista@test.com',
      rol: 'ANALISTA',
      nombre_completo: 'Ana',
      activo: true,
    });
    expect(auth.user?.rol).toBe('ANALISTA');
    expect(auth.canEdit({ usuario: 2 })).toBeTrue();
    expect(auth.canEdit({ usuario: 3 })).toBeFalse();
  });
  it('comparte una sola petición de refresh entre consumidores', () => {
    auth.setTokens({ access: 'old', refresh: 'refresh' });
    let count = 0;
    auth.refresh().subscribe(() => count++);
    auth.refresh().subscribe(() => count++);
    http.expectOne('/api/auth/refresh/').flush({ access: 'new' });
    expect(count).toBe(2);
    expect(auth.accessToken).toBe('new');
    auth.logout();
    expect(auth.accessToken).toBeNull();
    expect(auth.user).toBeNull();
  });
  it('ignora refresh tardío después de cerrar sesión', () => {
    auth.setTokens({ access: 'old', refresh: 'refresh' });
    auth.refresh().subscribe({ error: () => undefined });
    const pending = http.expectOne('/api/auth/refresh/');
    auth.logout();
    pending.flush({ access: 'late' });
    expect(auth.accessToken).toBeNull();
    expect(auth.user).toBeNull();
  });
  it('no mezcla una renovación anterior con el siguiente usuario', () => {
    auth.setTokens({ access: 'A', refresh: 'refreshA' });
    auth.refresh().subscribe({ error: () => undefined });
    const old = http.expectOne('/api/auth/refresh/');
    auth.logout();
    auth.login('b@test.com', 'secret').subscribe();
    http.expectOne('/api/auth/login/').flush({ access: 'B', refresh: 'refreshB' });
    http.expectOne('/api/auth/me/').flush({ id: 9, rol: 'VIEWER' });
    old.flush({ access: 'lateA' });
    expect(auth.accessToken).toBe('B');
    expect(auth.user?.id).toBe(9);
  });
});
