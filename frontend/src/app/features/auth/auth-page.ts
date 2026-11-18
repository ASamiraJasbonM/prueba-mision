import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { finalize, switchMap, tap, throwError } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AuthService } from '../../core/auth/auth.service';
import { errorCode, errorMessage, retryAfterSeconds } from '../../core/http/error-parser';
import { ApiBaseService } from '../../core/http/api-base.service';
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
        @if (!mfaRequired()) {
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
            /><mat-error>{{ register ? 'Mínimo 12 caracteres.' : 'Ingresa tu contraseña.' }}</mat-error></mat-form-field
          >
          @if (captchaImage()) {
            <section aria-label="Verificación CAPTCHA">
              <button type="button" mat-button (click)="loadCaptcha()" [disabled]="busy() || captchaLoading() || retrySeconds() > 0"
                aria-label="Obtener otra imagen de verificación">
                <img [src]="captchaImage()" alt="Reto CAPTCHA. Escribe los caracteres de la imagen." /> ↻
              </button>
              <mat-form-field><mat-label>Caracteres de la imagen</mat-label>
                <input matInput formControlName="captcha_answer" autocomplete="off" maxlength="32" />
                <mat-error>Completa la verificación.</mat-error>
              </mat-form-field>
            </section>
          }
          @if (error()) {
            <p role="alert" class="error-text">{{ error() }}</p>
          }
          <button mat-flat-button type="submit" [disabled]="busy() || captchaLoading() || retrySeconds() > 0">
            {{ busy() ? 'Un momento…' : register ? 'Crear cuenta' : 'Ingresar a DataPulse' }}
            <span aria-hidden="true">↗</span>
          </button>
        </form>
        } @else {
          <form [formGroup]="mfaForm" (ngSubmit)="submitMfa()">
            <p>Verifica tu identidad con el código de tu autenticador o un código de recuperación.</p>
            <mat-form-field><mat-label>Código de verificación o recuperación</mat-label>
              <input matInput formControlName="code" autocomplete="one-time-code" maxlength="32" />
              <mat-error>Usa 6 dígitos o un código de recuperación de 32 caracteres.</mat-error>
            </mat-form-field>
            @if (error()) { <p role="alert" class="error-text">{{ error() }}</p> }
            <button mat-flat-button type="submit" [disabled]="busy() || retrySeconds() > 0">Verificar identidad</button>
            <button mat-button type="button" (click)="restartMfa()" [disabled]="busy()">Volver al inicio de sesión</button>
          </form>
        }
        @if (retrySeconds() > 0) { <p role="status">Puedes intentar de nuevo en {{ retrySeconds() }} segundos.</p> }
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
  readonly captchaImage = signal('');
  readonly captchaLoading = signal(false);
  readonly mfaRequired = signal(false);
  readonly retrySeconds = signal(0);
  private registered = false;
  private readonly api = inject(ApiBaseService);
  private readonly destroyRef = inject(DestroyRef);
  private retryTimer: ReturnType<typeof setInterval> | undefined;
  readonly form = inject(FormBuilder).nonNullable.group({
    nombre_completo: ['', this.register ? [Validators.required, Validators.maxLength(150)] : []],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(this.register ? 12 : 8)]],
    captcha_key: [''],
    captcha_answer: [''],
  });
  readonly mfaForm = inject(FormBuilder).nonNullable.group({
    code: ['', [Validators.required, Validators.pattern(/^(?:\d{6}|[a-f0-9]{32})$/)]],
  });
  constructor() {
    this.destroyRef.onDestroy(() => {
      clearInterval(this.retryTimer);
      if (this.captchaImage()) URL.revokeObjectURL(this.captchaImage());
    });
  }
  loadCaptcha(): void {
    if (this.captchaLoading() || this.retrySeconds() > 0) return;
    this.captchaLoading.set(true);
    this.form.patchValue({ captcha_key: '', captcha_answer: '' });
    this.auth.captcha().pipe(switchMap((challenge) => {
        const url = this.api.captchaImageUrl(challenge.image_url);
        if (!url || !/^[a-f0-9]{40}$/.test(challenge.captcha_key)) {
          return throwError(() => new Error('Imagen de verificación inválida.'));
        }
        this.form.patchValue({ captcha_key: challenge.captcha_key, captcha_answer: '' });
        this.form.controls.captcha_answer.setValidators([Validators.required, Validators.maxLength(32)]);
        this.form.controls.captcha_answer.updateValueAndValidity();
        this.form.controls.captcha_key.setValidators(Validators.required);
        this.form.controls.captcha_key.updateValueAndValidity();
        // CORS fetch respects the backend's same-origin CORP. A blob URL then
        // renders locally, including deployments with a separate API origin.
        return this.api.captchaImage(url);
      }), takeUntilDestroyed(this.destroyRef), finalize(() => this.captchaLoading.set(false))).subscribe({
      next: (image) => {
        if (image.type !== 'image/png' || image.size > 1024 * 1024) {
          this.error.set('No se pudo cargar la imagen de verificación.');
          this.form.controls.captcha_key.reset('');
          return;
        }
        if (this.captchaImage()) URL.revokeObjectURL(this.captchaImage());
        this.captchaImage.set(URL.createObjectURL(image));
      },
      error: (error: unknown) => this.failed(error, false),
    });
  }
  submit(): void {
    if (this.form.invalid || this.busy() || this.captchaLoading() || this.retrySeconds() > 0) {
      this.form.markAllAsTouched();
      return;
    }
    this.busy.set(true);
    this.error.set('');
    const value = this.form.getRawValue();
    const captcha = this.captchaImage() ? { captcha_key: value.captcha_key, captcha_answer: value.captcha_answer } : undefined;
    const request = this.register && !this.registered
      ? this.auth
          .register({ email: value.email, password: value.password, nombre_completo: value.nombre_completo, ...captcha })
          .pipe(tap(() => {
            this.registered = true;
            if (this.captchaImage()) URL.revokeObjectURL(this.captchaImage());
            this.captchaImage.set('');
            this.form.controls.captcha_answer.clearValidators();
            this.form.controls.captcha_answer.updateValueAndValidity();
            this.form.controls.captcha_key.clearValidators();
            this.form.controls.captcha_key.updateValueAndValidity();
          }))
          .pipe(switchMap(() => this.auth.login(value.email, value.password)))
      : this.auth.login(value.email, value.password, captcha);
    request.pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.busy.set(false))).subscribe({
      next: (result) => {
        if ('mfa_required' in result) {
          this.mfaRequired.set(true);
          if (this.captchaImage()) URL.revokeObjectURL(this.captchaImage());
          this.captchaImage.set('');
          this.form.controls.password.reset('');
        } else this.navigateAfterLogin();
      },
      error: (e: unknown) => this.failed(e),
    });
  }
  submitMfa(): void {
    if (this.mfaForm.invalid || this.busy() || this.retrySeconds() > 0) {
      this.mfaForm.markAllAsTouched();
      return;
    }
    this.busy.set(true);
    this.error.set('');
    this.auth.verifyMfa(this.mfaForm.getRawValue().code).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => {
      this.busy.set(false);
      this.mfaForm.reset();
    })).subscribe({ next: () => this.navigateAfterLogin(), error: (error: unknown) => this.failed(error, false) });
  }
  restartMfa(): void {
    this.auth.cancelMfa();
    this.mfaRequired.set(false);
    this.mfaForm.reset();
    this.error.set('');
  }
  private navigateAfterLogin(): void {
    const path = this.route.snapshot.queryParamMap.get('returnUrl');
    void this.router.navigateByUrl(path?.startsWith('/') && !path.startsWith('//') && !path.includes('\\') ? path : '/dashboard');
  }
  private failed(error: unknown, refreshCaptcha = true): void {
    this.error.set(errorMessage(error));
    const wait = retryAfterSeconds(error);
    if (wait) {
      const deadline = Date.now() + wait * 1000;
      clearInterval(this.retryTimer);
      this.retrySeconds.set(wait);
      this.retryTimer = setInterval(() => {
        this.retrySeconds.set(Math.max(0, Math.ceil((deadline - Date.now()) / 1000)));
        if (!this.retrySeconds()) clearInterval(this.retryTimer);
      }, 1000);
    } else if (refreshCaptcha && (['captcha_required', 'captcha_invalid'].includes(errorCode(error) ?? '') || this.captchaImage())) {
      this.loadCaptcha();
    }
  }
}
