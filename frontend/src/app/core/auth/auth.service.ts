import { inject, Injectable } from '@angular/core';
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

const SESSION_KEY = 'datapulse.session';
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly api = inject(ApiBaseService);
  private tokens: Tokens | null = this.readTokens();
  private readonly profile = new BehaviorSubject<User | null>(null);
  private generation = 0;
  private refreshing: Observable<string> | null = null;
  private restoring: Observable<User | null> | null = null;
  readonly user$ = this.profile.asObservable();
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
  login(email: string, password: string): Observable<User> {
    const generation = ++this.generation;
    this.refreshing = null;
    this.restoring = null;
    return this.api.post<Tokens>('auth/login/', { email: email.trim(), password }).pipe(
      tap((tokens) => {
        if (generation !== this.generation) throw new Error('Sesión reemplazada.');
        this.setTokens(tokens);
      }),
      switchMap(() => this.loadProfile(generation)),
      catchError((error) => {
        if (generation === this.generation) this.logout();
        return throwError(() => error);
      }),
    );
  }
  register(data: { email: string; password: string; nombre_completo: string }): Observable<User> {
    return this.api.post<User>('auth/register/', data);
  }
  restore(): Observable<User | null> {
    if (this.user) return of(this.user);
    if (!this.tokens) return of(null);
    const generation = this.generation;
    if (!this.restoring)
      this.restoring = this.loadProfile(generation).pipe(
        catchError(() => {
          if (generation === this.generation) this.logout();
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
    this.tokens = tokens;
    try {
      localStorage.setItem(SESSION_KEY, JSON.stringify(tokens));
    } catch {
      /* Memory session remains usable. */
    }
  }
  logout(): void {
    this.generation++;
    this.refreshing = null;
    this.restoring = null;
    this.tokens = null;
    this.profile.next(null);
    try {
      localStorage.removeItem(SESSION_KEY);
    } catch {
      /* Storage can be unavailable. */
    }
  }
  private loadProfile(generation = this.generation): Observable<User> {
    return this.api.get<User>('auth/me/').pipe(
      tap((user) => {
        if (generation !== this.generation) throw new Error('Sesión reemplazada.');
        this.profile.next(user);
      }),
    );
  }
  private readTokens(): Tokens | null {
    try {
      const tokens: unknown = JSON.parse(localStorage.getItem(SESSION_KEY) ?? 'null');
      if (
        tokens &&
        typeof tokens === 'object' &&
        'access' in tokens &&
        typeof tokens.access === 'string' &&
        'refresh' in tokens &&
        typeof tokens.refresh === 'string'
      )
        return tokens as Tokens;
    } catch {
      /* A corrupt session is not a logged-in user. */
    }
    return null;
  }
}
