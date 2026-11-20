import { TestBed, fakeAsync, tick, discardPeriodicTasks } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { SyncStateService } from './sync-state.service';
import { SyncJob } from '../../shared/models/dto';

const job = (estado: SyncJob['estado']): SyncJob => ({
  id: 'f0000000-0000-4000-8000-000000000001', estado,
  estado_url: '/api/paises/sincronizaciones/f0000000-0000-4000-8000-000000000001/',
  progreso: {}, resultado: {}, creado: '', iniciado: null, terminado: null, intentos: 1,
});
describe('Async synchronization state', () => {
  let state: SyncStateService;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), SyncStateService] });
    state = TestBed.inject(SyncStateService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('keeps one request active and polls until a partial terminal result', fakeAsync(() => {
    state.start(); state.start();
    const request = http.expectOne(r => r.url.endsWith('/paises/sync-indicadores/'));
    expect(request.request.method).toBe('POST');
    request.flush(job('PENDIENTE'), { status: 202, statusText: 'Accepted' });
    expect(state.busy()).toBeTrue();
    tick(3000);
    http.expectOne(r => r.url.endsWith('/' + job('PENDIENTE').id + '/')).flush(job('EJECUTANDO'));
    tick(3000);
    http.expectOne(r => r.url.endsWith('/' + job('PENDIENTE').id + '/')).flush({
      ...job('PARCIAL'), resultado: { actualizados: 7, errores: [{ pais: 'AR', operacion: 'PIB', mensaje: 'Sin datos' }] },
    });
    expect(state.busy()).toBeFalse();
    expect(state.job()?.resultado.actualizados).toBe(7);
    tick(6000);
    http.expectNone(r => r.url.endsWith('/' + job('PENDIENTE').id + '/'));
  }));

  it('recovers a server job after navigation and preserves it when polling fails', fakeAsync(() => {
    state.resume();
    http.expectOne(r => r.url.endsWith('/paises/sincronizaciones/')).flush(job('EJECUTANDO'));
    tick(3000);
    http.expectOne(r => r.url.endsWith('/' + job('PENDIENTE').id + '/')).flush({}, { status: 503, statusText: 'Offline' });
    expect(state.busy()).toBeTrue();
    expect(state.error()).toContain('continúa en el servidor');
    state.resume();
    http.expectOne(r => r.url.endsWith('/paises/sincronizaciones/')).flush(job('COMPLETADA'));
    expect(state.busy()).toBeFalse();
    expect(state.error()).toBe('');
    discardPeriodicTasks();
  }));
});
