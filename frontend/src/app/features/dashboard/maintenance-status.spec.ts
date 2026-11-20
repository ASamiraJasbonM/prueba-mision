import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { ApiBaseService } from '../../core/http/api-base.service';
import { MaintenanceStatus } from './maintenance-status';

describe('Scheduled maintenance status', () => {
  it('keeps the previous success visible when the latest attempt failed', () => {
    const get = jasmine.createSpy().and.returnValue(of([{ tarea: 'indicadores',
      ultima_ejecucion: { estado: 'FALLIDA', iniciado: '2026-11-20T09:00:00Z', terminado: '2026-11-20T09:01:00Z',
        actualizados: 0, errores: [{ pais: 'CO', code: 'ConnectionError' }], ejecucion_url: null },
      ultimo_exito: { estado: 'COMPLETADA', terminado: '2026-11-19T09:01:00Z', actualizados: 182 },
    }]));
    TestBed.configureTestingModule({ providers: [{ provide: ApiBaseService, useValue: { get } }] });
    const fixture = TestBed.createComponent(MaintenanceStatus);
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('FALLIDA');
    expect(text).toContain('Último éxito');
    expect(text).toContain('182');
    expect(text).toContain('ConnectionError');
    fixture.destroy();
  });
  it('shows an explicit error and allows retry without claiming there were no runs', () => {
    const get = jasmine.createSpy().and.returnValues(throwError(() => new Error('private error')), of([]));
    TestBed.configureTestingModule({ providers: [{ provide: ApiBaseService, useValue: { get } }] });
    const fixture = TestBed.createComponent(MaintenanceStatus);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('No se pudo consultar');
    expect(fixture.nativeElement.textContent).not.toContain('private error');
    fixture.componentInstance.load();
    fixture.detectChanges();
    expect(get).toHaveBeenCalledTimes(2);
    expect(fixture.nativeElement.textContent).not.toContain('No se pudo consultar');
    fixture.destroy();
  });
});
