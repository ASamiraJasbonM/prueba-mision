import { TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { ConfirmDialogComponent } from './confirm-dialog.component';

describe('Reasoned confirmation', () => {
  it('requires an explicit reason before enabling the destructive confirmation', () => {
    TestBed.configureTestingModule({ providers: [
      { provide: MAT_DIALOG_DATA, useValue: { title: 'Corregir', message: 'Se conserva evidencia.', action: 'Eliminar', motivos: [{ value: 'DUPLICADO', label: 'Duplicado' }] } },
      { provide: MatDialogRef, useValue: { close: jasmine.createSpy() } },
    ] });
    const fixture = TestBed.createComponent(ConfirmDialogComponent);
    fixture.detectChanges();
    const button = fixture.nativeElement.querySelector('button[mat-flat-button]') as HTMLButtonElement;
    expect(button.disabled).toBeTrue();
    fixture.componentInstance.reason.setValue('DUPLICADO');
    fixture.detectChanges();
    expect(button.disabled).toBeFalse();
  });
});
