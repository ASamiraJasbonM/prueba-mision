import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { PortfolioStateService } from './portfolio-state.service';
describe('PortfolioStateService', () => {
  let state: PortfolioStateService;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), PortfolioStateService],
    });
    state = TestBed.inject(PortfolioStateService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());
  it('quotes If-Match, sends no DELETE body and refreshes after a close', () => {
    state.close(7, 3, 2).subscribe();
    const req = http.expectOne('/api/portafolios/7/posiciones/3/');
    expect(req.request.method).toBe('DELETE');
    expect(req.request.body).toBeNull();
    expect(req.request.headers.get('If-Match')).toBe('"2"');
    req.flush(null);
    expect(state.busy()).toBeTrue();
    http.expectOne('/api/portafolios/7/').flush({ id: 7, version: 3 });
    expect(state.detail()?.version).toBe(3);
    expect(state.busy()).toBeFalse();
  });
  it('hard-deletes a position via the eliminar endpoint and refreshes', () => {
    state.removePosition(7, 3, 2, 'DUPLICADO').subscribe();
    const req = http.expectOne('/api/portafolios/7/posiciones/3/eliminar/?motivo=DUPLICADO');
    expect(req.request.method).toBe('DELETE');
    expect(req.request.headers.get('If-Match')).toBe('"2"');
    req.flush(null, { status: 204, statusText: 'No Content' });
    http.expectOne('/api/portafolios/7/').flush({ id: 7, version: 3 });
    expect(state.detail()?.version).toBe(3);
    expect(state.busy()).toBeFalse();
  });
  it('refreshes on 409 and requires explicit resubmission', () => {
    let failed = false;
    state
      .update(7, { nombre: 'Demo', descripcion: '', es_publico: false, version: 2 })
      .subscribe({ error: () => (failed = true) });
    http.expectOne('/api/portafolios/7/').flush({}, { status: 409, statusText: 'Conflict' });
    http.expectOne('/api/portafolios/7/').flush({ id: 7, version: 4 });
    expect(state.detail()?.version).toBe(4);
    expect(state.conflict()).toBeTrue();
    expect(failed).toBeTrue();
  });
  it('bloquea nuevas escrituras si falla la relectura después de guardar', () => {
    state
      .update(7, { nombre: 'Demo', descripcion: '', es_publico: false, version: 2 })
      .subscribe({ error: () => undefined });
    http.expectOne('/api/portafolios/7/').flush({ id: 7 });
    http.expectOne('/api/portafolios/7/').flush({}, { status: 503, statusText: 'Unavailable' });
    expect(state.fresh()).toBeFalse();
    expect(state.busy()).toBeFalse();
  });
});
