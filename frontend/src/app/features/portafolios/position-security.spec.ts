import { TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { PositionForm } from './position-form';

describe('Contrato UTC y Decimal de posiciones', () => {
  const close = jasmine.createSpy('close');
  beforeEach(async () => {
    close.calls.reset();
    await TestBed.configureTestingModule({ imports: [PositionForm], providers: [
      { provide: MatDialogRef, useValue: { close } },
      { provide: MAT_DIALOG_DATA, useValue: { countries: [{ codigo_iso: 'CO', nombre: 'Colombia', moneda_codigo: 'COP' }],
        portfolio: { version: 3, posiciones: [] } } }
    ] }).compileComponents();
  });
  it('rechaza una fecha futura y no envía la posición', () => {
    const form = TestBed.createComponent(PositionForm).componentInstance;
    form.form.patchValue({ pais: 'CO', monto_inversion_usd: '1234.56', fecha_entrada: '2999-12-31' });
    form.submit();
    expect(form.form.controls.fecha_entrada.hasError('future')).toBeTrue();
    expect(close).not.toHaveBeenCalled();
  });
  it('conserva monto como string exacto y fecha como YYYY-MM-DD', () => {
    const form = TestBed.createComponent(PositionForm).componentInstance;
    form.form.patchValue({ pais: 'CO', monto_inversion_usd: '1234.50', fecha_entrada: '2020-01-02' });
    form.submit();
    expect(close).toHaveBeenCalledWith(jasmine.objectContaining({
      monto_inversion_usd: '1234.50', fecha_entrada: '2020-01-02', version: 3
    }));
  });
});
