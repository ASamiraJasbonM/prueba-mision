import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { AsyncValidatorFn, FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { catchError, finalize, map, of, switchMap, timer } from 'rxjs';
import { UiModule } from '../../shared/ui.module';
import { ApiBaseService } from '../../core/http/api-base.service';
import { AuthService } from '../../core/auth/auth.service';
import { Portfolio } from '../../shared/models/dto';
import { PortfolioStateService } from './portfolio-state.service';
import { errorMessage } from '../../core/http/error-parser';
@Component({
  imports: [UiModule],
  providers: [PortfolioStateService],
  template: `<a class="back-link" routerLink="/portafolios">← Portafolios</a>
    <div class="page-heading">
      <div>
        <p class="eyebrow">DALE FORMA A TU ESTRATEGIA</p>
        <h1>{{ id ? 'Editar' : 'Nuevo' }} portafolio<span class="heading-dot">.</span></h1>
      </div>
    </div>
    <section class="panel form-panel">
      @if (ready()) {
        <form [formGroup]="form" (ngSubmit)="save()">
          <mat-form-field
            ><mat-label>Nombre del portafolio</mat-label
            ><input matInput formControlName="nombre" maxlength="100" /><mat-hint
              >Entre 3 y 100 caracteres. Único para el propietario.</mat-hint
            ><mat-error>{{
              form.controls.nombre.hasError('taken')
                ? 'El propietario ya tiene un portafolio con este nombre.'
                : form.controls.nombre.hasError('unavailable')
                  ? 'No pudimos comprobar el nombre. Cambia el texto para reintentar.'
                  : 'Ingresa entre 3 y 100 caracteres.'
            }}</mat-error></mat-form-field
          ><mat-form-field
            ><mat-label>Descripción</mat-label
            ><textarea matInput formControlName="descripcion" rows="4" maxlength="500"></textarea
            ><mat-hint align="end"
              >{{ form.controls.descripcion.value.length }} / 500</mat-hint
            ></mat-form-field
          ><mat-checkbox formControlName="es_publico"
            >Compartir como portafolio público</mat-checkbox
          >
          <p class="fine-print">
            Otros usuarios podrán consultar y exportar el portafolio. La edición requiere permisos
            del propietario o administrador.
          </p>
          @if (state.conflict()) {
            <p class="notice" role="alert">
              Otro cambio actualizó este portafolio. Cargamos la versión vigente. Revisa los datos
              antes de guardar de nuevo.
            </p>
          }
          @if (id && !state.fresh() && !busy()) {
            <button mat-stroked-button (click)="reload()" type="button">
              Recargar versión vigente
            </button>
          }
          @if (error()) {
            <p role="alert" class="error-text">{{ error() }}</p>
          }
          <div class="form-actions">
            <a mat-button routerLink="/portafolios">Cancelar</a
            ><button
              mat-flat-button
              type="submit"
              [disabled]="busy() || form.pending || form.invalid || (!!id && !state.fresh())"
            >
              {{
                busy() ? 'Guardando…' : form.pending ? 'Comprobando nombre…' : 'Guardar portafolio'
              }}
            </button>
          </div>
        </form>
      } @else {
        <p role="status">{{ error() || 'Cargando portafolio…' }}</p>
      }
    </section>`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PortfolioForm {
  private api = inject(ApiBaseService);
  private auth = inject(AuthService);
  private router = inject(Router);
  readonly state = inject(PortfolioStateService);
  readonly id = Number(inject(ActivatedRoute).snapshot.paramMap.get('id')) || null;
  readonly ready = signal(!this.id);
  readonly busy = signal(false);
  readonly error = signal('');
  readonly form = inject(FormBuilder).nonNullable.group({
    nombre: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(100)]],
    descripcion: ['', Validators.maxLength(500)],
    es_publico: false,
  });
  constructor() {
    this.form.controls.nombre.addAsyncValidators(this.available());
    if (this.id)
      this.state.load(this.id).subscribe({
        next: (p) => {
          if (!this.auth.canEdit(p)) {
            void this.router.navigate(['/sin-permiso']);
            return;
          }
          this.form.patchValue(p);
          this.ready.set(true);
        },
        error: (e) => this.error.set(errorMessage(e)),
      });
  }
  private available(): AsyncValidatorFn {
    return (control) =>
      timer(350).pipe(
        switchMap(() =>
          this.api.get<{ disponible: boolean }>('portafolios/nombre-disponible/', {
            nombre: String(control.value).trim(),
            excluir_id: this.id,
          }),
        ),
        map((r) => (r.disponible ? null : { taken: true })),
        catchError(() => of({ unavailable: true })),
      );
  }
  reload(): void {
    if (this.id)
      this.state.load(this.id).subscribe({
        next: (p) => {
          this.form.patchValue(p);
          this.error.set('');
        },
        error: (e) => this.error.set(errorMessage(e)),
      });
  }
  save(): void {
    if (
      this.form.invalid ||
      this.form.pending ||
      this.busy() ||
      (!!this.id && !this.state.fresh())
    ) {
      this.form.markAllAsTouched();
      return;
    }
    this.busy.set(true);
    this.error.set('');
    const input = { ...this.form.getRawValue(), nombre: this.form.controls.nombre.value.trim() };
    const req = this.id
      ? this.state.update(this.id, { ...input, version: this.state.detail()!.version })
      : this.api.post<Portfolio>('portafolios/', input);
    req.pipe(finalize(() => this.busy.set(false))).subscribe({
      next: (p) => void this.router.navigate(['/portafolios', p.id]),
      error: (e) => {
        this.error.set(errorMessage(e));
        if (this.state.conflict() && this.state.detail())
          this.form.patchValue(this.state.detail()!);
      },
    });
  }
}
