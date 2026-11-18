import { DestroyRef, inject, Injectable } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import {
  BehaviorSubject,
  catchError,
  finalize,
  map,
  Observable,
  of,
  shareReplay,
  switchMap,
  tap,
  throwError,
} from 'rxjs';
import { ApiBaseService } from '../http/api-base.service';
import { Tokens, User } from '../../shared/models/dto';
import { CaptchaAnswer, CaptchaChallenge, LogoutReason, MfaPending } from './auth-types';

const SESSION_KEY = 'datapulse.session';
const ACCESS_KEY = 'datapulse.auth.access';
const REFRESH_KEY = 'datapulse.auth.refresh';
const CHANGE_KEY = 'datapulse.auth.change';
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly api = inject(ApiBaseService);
  private readonly router = inject(Router, { optional: true });
  private tokens: Tokens | null = this.readTokens();
  private readonly profile = new BehaviorSubject<User | null>(null);
  private generation = 0;
  private refreshing: Observable<string> | null = null;
  private restoring: Observable<User | null> | null = null;
  private pendingMfa: { token: string; generation: number } | null = null;
  readonly logoutReason = new BehaviorSubject<LogoutReason | null>(null);
  readonly user$ = this.profile.asObservable();
  constructor() {
    const storageChanged = (event: StorageEvent) => {
      if (event.storageArea && event.storageArea !== localStorage) return;
      if (event.key === null || ([ACCESS_KEY, REFRESH_KEY, CHANGE_KEY].includes(event.key) && event.newValue === null)) {
        if (this.tokens || this.pendingMfa) {
          this.clearSession('manual');
          void this.router?.navigate(['/login'], { queryParams: { returnUrl: this.router.url } });
        }
      } else if (event.key === CHANGE_KEY) {
        const incoming = this.readTokens();
        if (incoming?.refresh === this.tokens?.refresh) this.tokens = incoming;
        else if (this.tokens) {
          // A different login must not retain the previous account's view/state.
          this.clearSession('role_changed');
          void this.router?.navigate(['/login'], { queryParams: { returnUrl: this.router.url } });
        }
      }
    };
    window.addEventListener('storage', storageChanged);
    inject(DestroyRef).onDestroy(() => window.removeEventListener('storage', storageChanged));
  }
  get sessionId(): number {
    return this.generation;
  }
  get user(): User | null {
    return this.profile.value;
  }
  get accessToken(): string | null {
    return this.tokens?.access ?? null;
  }
  get hasRefresh(): boolean {
    return !!this.tokens?.refresh;
  }
  canWrite(): boolean {
    return this.user?.rol === 'ADMIN' || this.user?.rol === 'ANALISTA';
  }
  canEdit(portfolio: { usuario: number }): boolean {
    return (
      this.user?.rol === 'ADMIN' ||
      (this.user?.rol === 'ANALISTA' && this.user.id === portfolio.usuario)
    );
  }
  hasRole(...roles: User['rol'][]): boolean {
    return !!this.user && roles.includes(this.user.rol);
  }
  login(email: string, password: string, captcha?: CaptchaAnswer): Observable<User | MfaPending> {
    const generation = ++this.generation;
    this.refreshing = null;
    this.restoring = null;
    this.pendingMfa = null;
    return this.api.post<unknown>('auth/login/', { email: email.trim(), password, ...captcha }).pipe(
      switchMap((result) => {
        if (generation !== this.generation) throw new Error('Sesión reemplazada.');
        if (result && typeof result === 'object' && 'mfa_required' in result && result.mfa_required === true &&
            'mfa_token' in result && typeof result.mfa_token === 'string' && result.mfa_token.length > 0) {
          this.pendingMfa = { token: result.mfa_token, generation };
          return of<MfaPending>({ mfa_required: true });
        }
        return this.completeLogin(result, generation);
      }),
    );
  }
  verifyMfa(code: string): Observable<User> {
    const pending = this.pendingMfa;
    if (!pending || pending.generation !== this.generation) return throwError(() => new Error('Inicia sesión de nuevo.'));
    return this.api.post<unknown>('auth/mfa/verify-login/', { mfa_token: pending.token, code }).pipe(
      switchMap((tokens) => {
        if (pending.generation !== this.generation) throw new Error('Sesión reemplazada.');
        this.pendingMfa = null;
        return this.completeLogin(tokens, pending.generation);
      }),
    );
  }
  captcha(): Observable<CaptchaChallenge> {
    return this.api.get<CaptchaChallenge>('auth/captcha/');
  }
  cancelMfa(): void {
    this.pendingMfa = null;
    this.generation++;
  }
  register(data: { email: string; password: string; nombre_completo: string } & Partial<CaptchaAnswer>): Observable<User> {
    return this.api.post<User>('auth/register/', data);
  }
  restore(): Observable<User | null> {
    if (this.user) return of(this.user);
    if (!this.tokens) return of(null);
    const generation = this.generation;
    if (!this.restoring)
      this.restoring = this.loadProfile(generation).pipe(
        catchError((error: unknown) => {
          if (generation === this.generation && error instanceof HttpErrorResponse && error.status === 401) this.logout('expired');
          return of(null);
        }),
        finalize(() => {
          if (generation === this.generation) this.restoring = null;
        }),
        shareReplay({ bufferSize: 1, refCount: false }),
      );
    return this.restoring;
  }
  refresh(): Observable<string> {
    if (!this.tokens) return throwError(() => new Error('Sesión no disponible.'));
    const generation = this.generation;
    const refreshToken = this.tokens.refresh;
    if (!this.refreshing)
      this.refreshing = this.api
        .post<{ access: string; refresh?: string }>('auth/refresh/', {
          refresh: this.tokens.refresh,
        })
        .pipe(
          tap((tokens) => {
            if (generation !== this.generation) throw new Error('Sesión reemplazada.');
            this.setTokens({ access: tokens.access, refresh: tokens.refresh ?? refreshToken });
          }),
          map((tokens) => tokens.access),
          finalize(() => {
            if (generation === this.generation) this.refreshing = null;
          }),
          shareReplay({ bufferSize: 1, refCount: false }),
        );
    return this.refreshing;
  }
  setTokens(tokens: Tokens): void {
    if (!this.validTokens(tokens)) throw new Error('Respuesta de sesión inválida.');
    this.tokens = tokens;
    try {
      localStorage.setItem(ACCESS_KEY, tokens.access);
      localStorage.setItem(REFRESH_KEY, tokens.refresh);
      localStorage.setItem(CHANGE_KEY, crypto.randomUUID());
      localStorage.removeItem(SESSION_KEY);
    } catch {
      /* Memory session remains usable. */
    }
  }
  logout(reason: LogoutReason = 'manual'): void {
    this.clearSession(reason);
    try {
      localStorage.removeItem(ACCESS_KEY);
      localStorage.removeItem(REFRESH_KEY);
      localStorage.removeItem(CHANGE_KEY);
      localStorage.removeItem(SESSION_KEY);
    } catch { /* Storage can be unavailable. */ }
  }
  private clearSession(reason: LogoutReason): void {
    this.generation++;
    this.refreshing = null;
    this.restoring = null;
    this.tokens = null;
    this.profile.next(null);
    this.pendingMfa = null;
    this.logoutReason.next(reason);
  }
  private completeLogin(tokens: unknown, generation: number): Observable<User> {
    if (!this.validTokens(tokens)) return throwError(() => new Error('Respuesta de sesión inválida.'));
    this.profile.next(null);
    this.setTokens(tokens);
    return this.loadProfile(generation);
  }
  reloadProfile(): Observable<User> {
    return this.loadProfile();
  }
  private validTokens(tokens: unknown): tokens is Tokens {
    return !!tokens && typeof tokens === 'object' && 'access' in tokens && typeof tokens.access === 'string' &&
      tokens.access.length > 0 && 'refresh' in tokens && typeof tokens.refresh === 'string' && tokens.refresh.length > 0;
  }
  private loadProfile(generation = this.generation): Observable<User> {
    return this.api.get<User>('auth/me/').pipe(
      tap((user) => {
        if (generation !== this.generation) throw new Error('Sesión reemplazada.');
        const previousRole = this.user?.rol;
        this.profile.next(user);
        if (previousRole && previousRole !== user.rol && this.router) {
          let route = this.router.routerState.snapshot.root;
          while (route.firstChild) route = route.firstChild;
          const roles: unknown = route.data['roles'];
          if (Array.isArray(roles) && !roles.includes(user.rol)) void this.router.navigate(['/sin-permiso']);
        }
      }),
    );
  }
  private readTokens(): Tokens | null {
    try {
      const access = localStorage.getItem(ACCESS_KEY);
      const refresh = localStorage.getItem(REFRESH_KEY);
      if (access && refresh) return { access, refresh };
      const tokens: unknown = JSON.parse(localStorage.getItem(SESSION_KEY) ?? 'null');
      if (this.validTokens(tokens)) return tokens;
    } catch {
      /* A corrupt session is not a logged-in user. */
    }
    return null;
  }
}
