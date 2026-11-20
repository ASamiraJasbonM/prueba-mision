import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { AbstractControl, FormBuilder, ValidationErrors, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { UiModule } from '../../shared/ui.module';
import { ASSETS, Country, PortfolioDetail, Position } from '../../shared/models/dto';
import { formatMoneyInput, moneyUnits, normalizeMoney } from '../../shared/utils/decimal';
import { utcToday } from '../../shared/utils/dates';
export interface PositionDialogData {
  countries: Country[];
  portfolio: PortfolioDetail;
  position?: Position;
}
export function amountValidator(control: AbstractControl): ValidationErrors | null {
  const value = moneyUnits(String(control.value));
  return value === null || value < 100000n || value > 1000000000n ? { amount: true } : null;
}
@Component({
  imports: [UiModule],
  template: `<h2 mat-dialog-title>{{ data.position ? 'Editar' : 'Nueva' }} posición</h2>
    <mat-dialog-content
      ><form [formGroup]="form" id="position-form" (ngSubmit)="submit()">
        <p class="muted">Importes en USD · Fechas en UTC</p>
        <mat-form-field
          ><mat-label>Buscar país</mat-label
          ><input
            matInput
            formControlName="pais"
            [matAutocomplete]="countriesAuto"
            placeholder="Nombre o código"
          /><mat-autocomplete #countriesAuto="matAutocomplete" [displayWith]="displayCountry">
            @for (c of filteredCountries(); track c.codigo_iso) {
              <mat-option [value]="c.codigo_iso">{{ c.nombre }} · {{ c.codigo_iso }}</mat-option>
            }</mat-autocomplete
          ><mat-error>Selecciona un país válido.</mat-error></mat-form-field
        ><mat-form-field
          ><mat-label>Tipo de activo</mat-label
          ><mat-select formControlName="tipo_activo">
            @for (asset of assets; track asset.value) {
              <mat-option [value]="asset.value">{{ asset.label }}</mat-option>
            }
          </mat-select></mat-form-field
        ><mat-form-field
          ><mat-label>Monto de inversión USD</mat-label
          ><input
            matInput
            inputmode="decimal"
            formControlName="monto_inversion_usd"
            (input)="formatAmount($event)"
            placeholder="1,000.00"
          /><mat-hint>1,000 a 10,000,000 USD · coma para miles, punto decimal (1,234.56)</mat-hint
          ><mat-error>Ingresa un importe válido dentro del rango.</mat-error></mat-form-field
        ><mat-form-field
          ><mat-label>Fecha de entrada</mat-label
          ><input matInput type="date" formControlName="fecha_entrada" [max]="today" /><mat-error
            >La fecha no puede ser futura.</mat-error
          ></mat-form-field
        ><mat-form-field
          ><mat-label>Notas</mat-label
          ><textarea matInput formControlName="notas" maxlength="200" rows="2"></textarea>
        </mat-form-field>
        @if (form.hasError('currency')) {
          <p class="error-text">No se permite MONEDA en países cuya moneda es USD.</p>
        }
        @if (form.hasError('duplicates')) {
          <p class="error-text">Ya existen dos posiciones activas del mismo país y tipo.</p>
        }
        @if (form.hasError('total')) {
          <p class="error-text">El total activo no puede superar 50.000.000 USD.</p>
        }
      </form></mat-dialog-content
    ><mat-dialog-actions align="end"
      ><button mat-button [mat-dialog-close]="null">Cancelar</button
      ><button mat-flat-button type="submit" form="position-form" [disabled]="form.invalid">
        Aplicar posición
      </button></mat-dialog-actions
    >`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PositionForm {
  readonly data = inject<PositionDialogData>(MAT_DIALOG_DATA);
  private ref = inject(MatDialogRef<PositionForm>);
  readonly assets = ASSETS;
  readonly today = utcToday();
  readonly form = inject(FormBuilder).nonNullable.group(
    {
      pais: [
        this.data.position?.pais ?? '',
        [
          Validators.required,
          (c: AbstractControl) =>
            this.data.countries.some((p) => p.codigo_iso === c.value) ? null : { country: true },
        ],
      ],
      tipo_activo: [this.data.position?.tipo_activo ?? 'RENTA_FIJA', Validators.required],
      monto_inversion_usd: [
        formatMoneyInput(this.data.position?.monto_inversion_usd ?? ''),
        [Validators.required, amountValidator],
      ],
      fecha_entrada: [
        this.data.position?.fecha_entrada ?? this.today,
        [
          Validators.required,
          (c: AbstractControl) =>
            /^\d{4}-\d{2}-\d{2}$/.test(c.value) && c.value <= this.today ? null : { future: true },
        ],
      ],
      notas: [this.data.position?.notas ?? '', Validators.maxLength(200)],
    },
    { validators: () => this.validateDomain() },
  );
  constructor() {
    this.form.updateValueAndValidity();
  }
  formatAmount(event: Event): void {
    const input = event.target as HTMLInputElement;
    const original = input.value;
    // Typing/deleting can temporarily move existing grouping commas. Pasted input
    // still follows the strict parser so malformed amounts are not silently accepted.
    const editing = event instanceof InputEvent &&
      /^(insertText|deleteContentBackward|deleteContentForward|deleteByCut)$/.test(event.inputType);
    const text = editing && /^[\d,]+(\.\d{0,2})?$/.test(original)
      ? original.replaceAll(',', '') : original;
    const formatted = formatMoneyInput(text);
    if (formatted === original) return;
    const offset = original.slice(0, input.selectionStart ?? original.length).replaceAll(',', '').length;
    this.form.controls.monto_inversion_usd.setValue(formatted);
    input.value = formatted;
    let caret = 0;
    let consumed = 0;
    while (caret < formatted.length && consumed < offset) {
      if (formatted[caret] !== ',') consumed++;
      caret++;
    }
    input.setSelectionRange(caret, caret);
  }
  displayCountry = (code: string): string =>
    this.data.countries.find((c) => c.codigo_iso === code)?.nombre ?? code;
  filteredCountries(): Country[] {
    const text = this.form.controls.pais.value.toLocaleLowerCase();
    return this.data.countries.filter(
      (c) =>
        c.nombre.toLocaleLowerCase().includes(text) ||
        c.codigo_iso.toLocaleLowerCase().includes(text),
    );
  }
  private validateDomain(): ValidationErrors | null {
    if (!this.form) return null;
    const f = this.form.getRawValue();
    const country = this.data.countries.find((c) => c.codigo_iso === f.pais);
    if (country?.moneda_codigo === 'USD' && f.tipo_activo === 'MONEDA') return { currency: true };
    const active = this.data.portfolio.posiciones.filter(
      (p) => !p.fecha_salida && p.id !== this.data.position?.id,
    );
    if (active.filter((p) => p.pais === f.pais && p.tipo_activo === f.tipo_activo).length >= 2)
      return { duplicates: true };
    const total =
      active.reduce((sum, p) => sum + (moneyUnits(p.monto_inversion_usd) ?? 0n), 0n) +
      (moneyUnits(f.monto_inversion_usd) ?? 0n);
    return total > 5000000000n ? { total: true } : null;
  }
  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    this.ref.close({
      ...value,
      monto_inversion_usd: normalizeMoney(value.monto_inversion_usd),
      version: this.data.portfolio.version,
    });
  }
}
