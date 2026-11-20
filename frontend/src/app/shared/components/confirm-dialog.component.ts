import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { FormControl, Validators } from '@angular/forms';
import { UiModule } from '../ui.module';
@Component({
  selector: 'app-confirm-dialog',
  imports: [MatDialogModule, MatButtonModule, UiModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<h2 mat-dialog-title>{{ data.title }}</h2>
    <mat-dialog-content><p>{{ data.message }}</p>
      @if (data.motivos) {
        <mat-form-field><mat-label>Motivo</mat-label><mat-select [formControl]="reason">
          @for (motivo of data.motivos; track motivo.value) { <mat-option [value]="motivo.value">{{ motivo.label }}</mat-option> }
        </mat-select><mat-error>Selecciona un motivo.</mat-error></mat-form-field>
      }
    </mat-dialog-content><mat-dialog-actions align="end"
      ><button mat-button [mat-dialog-close]="false">Cancelar</button
      ><button mat-flat-button [disabled]="!!data.motivos && reason.invalid" [mat-dialog-close]="data.motivos ? reason.value : true">
        {{ data.action || 'Confirmar' }}
      </button></mat-dialog-actions
    >`,
})
export class ConfirmDialogComponent {
  readonly data = inject<{ title: string; message: string; action?: string; motivos?: {value: string; label: string}[] }>(MAT_DIALOG_DATA);
  readonly reason = new FormControl('', { nonNullable: true, validators: [Validators.required] });
}
