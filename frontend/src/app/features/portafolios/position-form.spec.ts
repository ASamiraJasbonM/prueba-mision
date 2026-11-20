import { FormControl } from '@angular/forms';
import { TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { PositionForm, amountValidator } from './position-form';
describe('PositionForm', () => {
  it('groups typed amounts without losing cents and submits the canonical decimal', async () => {
    const close = jasmine.createSpy('close');
    await TestBed.configureTestingModule({
      imports: [PositionForm], providers: [
        { provide: MatDialogRef, useValue: { close } },
        { provide: MAT_DIALOG_DATA, useValue: { countries: [{ codigo_iso: 'CO', nombre: 'Colombia', moneda_codigo: 'COP' }],
          portfolio: { version: 3, posiciones: [] } } },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(PositionForm);
    fixture.detectChanges();
    const component = fixture.componentInstance;
    component.form.patchValue({ pais: 'CO', fecha_entrada: '2026-01-01' });
    const input = fixture.nativeElement.querySelector('input[formControlName="monto_inversion_usd"]') as HTMLInputElement;
    input.focus();
    input.value = '1234567.20';
    input.setSelectionRange(10, 10);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    fixture.detectChanges();
    expect(input.value).toBe('1,234,567.20');
    component.submit();
    expect(close).toHaveBeenCalledWith(jasmine.objectContaining({ monto_inversion_usd: '1234567.20', version: 3 }));
    input.value = '12345.20';
    input.setSelectionRange(2, 2);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    expect(input.value).toBe('12,345.20');
    expect(input.selectionStart).toBe(2);
    input.value = '1,2345.20';
    input.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: '5' }));
    expect(input.value).toBe('12,345.20');
    input.value = '12,34.20';
    input.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'deleteContentBackward' }));
    expect(input.value).toBe('1,234.20');
    input.value = '12,34.20';
    input.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertFromPaste' }));
    expect(input.value).toBe('12,34.20');
    expect(component.form.controls.monto_inversion_usd.invalid).toBeTrue();
    input.value = '1234.';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    expect(input.value).toBe('1,234.');
    expect(component.form.controls.monto_inversion_usd.invalid).toBeTrue();
    input.value = '1000.001';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    fixture.detectChanges();
    expect(input.value).toBe('1000.001');
    expect(component.form.controls.monto_inversion_usd.invalid).toBeTrue();
  });
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
