import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter, Router, Navigation } from '@angular/router';
import { AuthService } from '../auth/auth.service';
import { NotificationService } from '../state/notification.service';
import { LoadingService } from '../state/loading.service';
import { jwtInterceptor } from './jwt.interceptor';
import { errorInterceptor } from './error.interceptor';
import { loadingInterceptor } from './loading.interceptor';

describe('Interceptores HTTP', () => {
  let http: HttpClient;
  let controller: HttpTestingController;
  let auth: AuthService;
  const notification = jasmine.createSpyObj<NotificationService>('Notification', ['show']);
  beforeEach(() => {
    localStorage.clear();
    notification.show.calls.reset();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([loadingInterceptor, errorInterceptor, jwtInterceptor])),
        provideHttpClientTesting(),
        { provide: NotificationService, useValue: notification },
      ],
    });
    http = TestBed.inject(HttpClient);
    controller = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(AuthService);
  });
  afterEach(() => {
    controller.verify();
    localStorage.clear();
  });
  it('adjunta JWT solo a la API y respeta solicitudes concurrentes', () => {
    auth.setTokens({ access: 'token', refresh: 'refresh' });
    let loading = false;
    const subscription = TestBed.inject(LoadingService).loading$.subscribe(
      (value) => (loading = value),
    );
    http.get('/api/paises/').subscribe();
    http.get('/assets/geojson/latam.geojson').subscribe();
    const api = controller.expectOne('/api/paises/');
    const asset = controller.expectOne('/assets/geojson/latam.geojson');
    expect(api.request.headers.get('Authorization')).toBe('Bearer token');
    expect(asset.request.headers.has('Authorization')).toBeFalse();
    api.flush({});
    expect(loading).toBeTrue();
    asset.flush({});
    expect(loading).toBeFalse();
    subscription.unsubscribe();
  });
  it('notifica un error de negocio sin ocultar el fallo al componente', () => {
    let status = 0;
    http.get('/api/paises/').subscribe({ error: (error) => (status = error.status) });
    controller
      .expectOne('/api/paises/')
      .flush(
        { error: { code: 'conflict', message: 'Actualiza el portafolio.', details: {} } },
        { status: 409, statusText: 'Conflict' },
      );
    expect(status).toBe(409);
    expect(notification.show).toHaveBeenCalledWith('Actualiza el portafolio.');
  });
  it('limpia la sesión y redirige si el refresh también vence', () => {
    const router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    auth.setTokens({ access: 'expired', refresh: 'expired-refresh' });
    http.get('/api/paises/').subscribe({ error: () => undefined });
    controller.expectOne('/api/paises/').flush({}, { status: 401, statusText: 'Unauthorized' });
    controller
      .expectOne('/api/auth/refresh/')
      .flush({}, { status: 401, statusText: 'Unauthorized' });
    expect(auth.accessToken).toBeNull();
    expect(router.navigate).toHaveBeenCalled();
  });
  it('renueva una sola vez y reintenta las consultas concurrentes con el token nuevo', () => {
    auth.setTokens({ access: 'old', refresh: 'refresh' });
    let completed = 0;
    http.get('/api/paises/').subscribe(() => completed++);
    http.get('/api/riesgo/').subscribe(() => completed++);
    controller.expectOne('/api/paises/').flush({}, { status: 401, statusText: 'Unauthorized' });
    controller.expectOne('/api/riesgo/').flush({}, { status: 401, statusText: 'Unauthorized' });
    controller.expectOne('/api/auth/refresh/').flush({ access: 'new' });
    const countries = controller.expectOne('/api/paises/');
    const risks = controller.expectOne('/api/riesgo/');
    expect(countries.request.headers.get('Authorization')).toBe('Bearer new');
    expect(risks.request.headers.get('Authorization')).toBe('Bearer new');
    countries.flush({});
    risks.flush({});
    expect(completed).toBe(2);
  });
  it('conserva la ruta solicitada cuando vence la sesión durante la navegación inicial', () => {
    const router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    spyOn(router, 'getCurrentNavigation').and.returnValue({
      extractedUrl: router.parseUrl('/portafolios/7/editar'),
    } as Navigation);
    auth.setTokens({ access: 'expired', refresh: 'expired-refresh' });
    http.get('/api/auth/me/').subscribe({ error: () => undefined });
    controller.expectOne('/api/auth/me/').flush({}, { status: 401, statusText: 'Unauthorized' });
    controller
      .expectOne('/api/auth/refresh/')
      .flush({}, { status: 401, statusText: 'Unauthorized' });
    expect(router.navigate).toHaveBeenCalledWith(['/login'], {
      queryParams: { returnUrl: '/portafolios/7/editar' },
    });
  });
});
