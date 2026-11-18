import { FormControl } from '@angular/forms';
import { TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { PositionForm, amountValidator } from './position-form';
describe('PositionForm', () => {
  it('validates monetary boundaries exactly', () => {
    for (const value of ['999.99', '10000000.01', '1e5', 'NaN', '1000.001'])
      expect(amountValidator(new FormControl(value))).not.toBeNull();
    for (const value of ['1000.00', '10000000.00', '1,234.56'])
      expect(amountValidator(new FormControl(value))).toBeNull();
  });
  it('renders a reactive form and forbids currency in a USD country', async () => {
    await TestBed.configureTestingModule({
      imports: [PositionForm],
      providers: [
        { provide: MatDialogRef, useValue: { close: jasmine.createSpy('close') } },
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            countries: [{ codigo_iso: 'EC', nombre: 'Ecuador', moneda_codigo: 'USD' }],
            portfolio: { version: 1, posiciones: [] },
          },
        },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(PositionForm);
    fixture.detectChanges();
    const page = fixture.componentInstance;
    page.form.patchValue({ pais: 'EC', tipo_activo: 'MONEDA', monto_inversion_usd: '1000.00' });
    expect(page.form.hasError('currency')).toBeTrue();
    expect(fixture.nativeElement.querySelector('form')).toBeTruthy();
  });
});
