import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { finalize, switchMap } from 'rxjs';
import { AuthService } from '../../core/auth/auth.service';
import { errorMessage } from '../../core/http/error-parser';
import { UiModule } from '../../shared/ui.module';
@Component({
  imports: [UiModule],
  template: `<main class="auth-layout">
    <section class="auth-story">
      <a class="brand" routerLink="/"
        >D<span>◈</span> DataPulse<small>LATAM · INTELIGENCIA FINANCIERA</small></a
      >
      <div>
        <p class="eyebrow">UNA REGIÓN. MÁS PERSPECTIVAS.</p>
        <h1>Entiende el contexto.<br /><em>Invierte con criterio.</em></h1>
        <p>
          Indicadores, riesgo país y tus inversiones.<br />Una visión conectada de Latinoamérica.
        </p>
        <div class="auth-grid">
          <span>10<small>economías</small></span
          ><span>6<small>indicadores clave</small></span
          ><span>01<small>panorama regional</small></span>
        </div>
      </div>
      <small>DATOS CON CONTEXTO. DECISIONES INFORMADAS.</small>
    </section>
    <section class="auth-form">
      <div>
        <p class="eyebrow">BIENVENIDO A DATAPULSE</p>
        <h2>{{ register ? 'Crea tu cuenta' : 'Tu próxima decisión empieza aquí' }}</h2>
        <p class="muted">
          {{
            register
              ? 'Una nueva perspectiva sobre tus inversiones.'
              : 'Ingresa para explorar el pulso de la región.'
          }}
        </p>
        <form [formGroup]="form" (ngSubmit)="submit()">
          @if (register) {
            <mat-form-field
              ><mat-label>Nombre completo</mat-label
              ><input matInput formControlName="nombre_completo" autocomplete="name" /><mat-error
                >Ingresa tu nombre (máximo 150 caracteres).</mat-error
              ></mat-form-field
            >
          }
          <mat-form-field
            ><mat-label>Correo electrónico</mat-label
            ><input matInput type="email" formControlName="email" autocomplete="email" /><mat-error
              >Ingresa un correo válido.</mat-error
            ></mat-form-field
          >
          <mat-form-field
            ><mat-label>Contraseña</mat-label
            ><input
              matInput
              type="password"
              formControlName="password"
              [attr.autocomplete]="register ? 'new-password' : 'current-password'"
            /><mat-error>Mínimo 8 caracteres.</mat-error></mat-form-field
          >
          @if (error()) {
            <p role="alert" class="error-text">{{ error() }}</p>
          }
          <button mat-flat-button type="submit" [disabled]="busy()">
            {{ busy() ? 'Un momento…' : register ? 'Crear cuenta' : 'Ingresar a DataPulse' }}
            <span aria-hidden="true">↗</span>
          </button>
        </form>
        <p class="auth-switch">
          {{ register ? '¿Ya tienes una cuenta?' : '¿Primera vez por aquí?' }}
          <a [routerLink]="register ? '/login' : '/registro'">{{
            register ? 'Inicia sesión' : 'Crea una cuenta'
          }}</a>
        </p>
        <p class="fine-print">
          Los indicadores pueden ser parciales. Revisa siempre las fuentes y fechas de
          actualización.
        </p>
      </div>
    </section>
  </main>`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthPage {
  readonly auth = inject(AuthService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  readonly register = !!this.route.snapshot.data['register'];
  readonly busy = signal(false);
  readonly error = signal('');
  readonly form = inject(FormBuilder).nonNullable.group({
    nombre_completo: ['', this.register ? [Validators.required, Validators.maxLength(150)] : []],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });
  submit(): void {
    if (this.form.invalid || this.busy()) {
      this.form.markAllAsTouched();
      return;
    }
    this.busy.set(true);
    this.error.set('');
    const value = this.form.getRawValue();
    const request = this.register
      ? this.auth
          .register(value)
          .pipe(switchMap(() => this.auth.login(value.email, value.password)))
      : this.auth.login(value.email, value.password);
    request.pipe(finalize(() => this.busy.set(false))).subscribe({
      next: () => {
        const path = this.route.snapshot.queryParamMap.get('returnUrl');
        void this.router.navigateByUrl(
          path?.startsWith('/') && !path.startsWith('//') ? path : '/dashboard',
        );
      },
      error: (e) => this.error.set(errorMessage(e)),
    });
  }
}
