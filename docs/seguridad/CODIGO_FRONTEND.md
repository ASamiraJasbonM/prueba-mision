# Código completo del endurecimiento Angular

Snapshot de archivos clave; fuente editable en el árbol del proyecto.

## frontend/package.json

```json
{
  "name": "datapulse",
  "version": "0.0.0",
  "scripts": {
    "ng": "ng",
    "start": "ng serve --host 127.0.0.1 --proxy-config proxy.conf.json",
    "build": "ng build",
    "postbuild": "node docker/finalize-index.mjs && node docker/check-production.mjs",
    "audit:prod": "npm audit --omit=dev --audit-level=high",
    "watch": "ng build --watch --configuration development",
    "test": "ng test",
    "test:ci": "ng test --watch=false --browsers=ChromeHeadless"
  },
  "prettier": {
    "printWidth": 100,
    "singleQuote": true,
    "overrides": [
      {
        "files": "*.html",
        "options": {
          "parser": "angular"
        }
      }
    ]
  },
  "private": true,
  "dependencies": {
    "@angular/cdk": "20.2.14",
    "@angular/common": "^20.3.0",
    "@angular/compiler": "^20.3.0",
    "@angular/core": "^20.3.0",
    "@angular/forms": "^20.3.0",
    "@angular/material": "20.2.14",
    "@angular/platform-browser": "^20.3.0",
    "@angular/router": "^20.3.0",
    "@fontsource-variable/dm-sans": "5.3.0",
    "@fontsource-variable/source-serif-4": "5.3.1",
    "chart.js": "4.6.1",
    "leaflet": "1.9.4",
    "rxjs": "~7.8.0",
    "tslib": "^2.3.0",
    "zone.js": "~0.15.0"
  },
  "devDependencies": {
    "@angular/build": "^20.3.43",
    "@angular/cli": "^20.3.43",
    "@angular/compiler-cli": "^20.3.0",
    "@types/geojson": "7946.0.16",
    "@types/jasmine": "~5.1.0",
    "@types/leaflet": "1.9.22",
    "jasmine-core": "~5.9.0",
    "karma": "~6.4.0",
    "karma-chrome-launcher": "~3.2.0",
    "karma-coverage": "~2.2.0",
    "karma-jasmine": "~5.1.0",
    "karma-jasmine-html-reporter": "~2.1.0",
    "typescript": "~5.9.2"
  }
}
```

## frontend/angular.json

```json
{
  "$schema": "./node_modules/@angular/cli/lib/config/schema.json",
  "version": 1,
  "newProjectRoot": "projects",
  "projects": {
    "datapulse": {
      "projectType": "application",
      "schematics": {
        "@schematics/angular:component": {
          "style": "scss"
        }
      },
      "root": "",
      "sourceRoot": "src",
      "prefix": "app",
      "architect": {
        "build": {
          "builder": "@angular/build:application",
          "options": {
            "browser": "src/main.ts",
            "polyfills": ["zone.js"],
            "tsConfig": "tsconfig.app.json",
            "inlineStyleLanguage": "scss",
            "assets": [
              {
                "glob": "**/*",
                "input": "public"
              }
            ],
            "styles": [
              "node_modules/@fontsource-variable/dm-sans/index.css",
              "node_modules/@fontsource-variable/source-serif-4/index.css",
              "node_modules/leaflet/dist/leaflet.css",
              "src/styles.scss"
            ],
            "allowedCommonJsDependencies": ["leaflet"]
          },
          "configurations": {
            "production": {
              "sourceMap": false,
              "optimization": true,
              "namedChunks": false,
              "budgets": [
                {
                  "type": "initial",
                  "maximumWarning": "600kB",
                  "maximumError": "1MB"
                },
                {
                  "type": "anyComponentStyle",
                  "maximumWarning": "4kB",
                  "maximumError": "8kB"
                }
              ],
              "outputHashing": "all",
              "fileReplacements": [
                {
                  "replace": "src/environments/environment.ts",
                  "with": "src/environments/environment.prod.ts"
                }
              ]
            },
            "development": {
              "optimization": false,
              "extractLicenses": false,
              "sourceMap": true
            }
          },
          "defaultConfiguration": "production"
        },
        "serve": {
          "builder": "@angular/build:dev-server",
          "configurations": {
            "production": {
              "buildTarget": "datapulse:build:production"
            },
            "development": {
              "buildTarget": "datapulse:build:development"
            }
          },
          "defaultConfiguration": "development"
        },
        "extract-i18n": {
          "builder": "@angular/build:extract-i18n"
        },
        "test": {
          "builder": "@angular/build:karma",
          "options": {
            "polyfills": ["zone.js", "zone.js/testing"],
            "tsConfig": "tsconfig.spec.json",
            "inlineStyleLanguage": "scss",
            "assets": [
              {
                "glob": "**/*",
                "input": "public"
              }
            ],
            "styles": [
              "node_modules/@fontsource-variable/dm-sans/index.css",
              "node_modules/@fontsource-variable/source-serif-4/index.css",
              "node_modules/leaflet/dist/leaflet.css",
              "src/styles.scss"
            ]
          }
        }
      }
    }
  }
}
```

## frontend/nginx.conf

```
# Maps live at http scope; a single server-level add_header avoids location inheritance gaps.
map $scheme $datapulse_hsts {
    default "";
    https "max-age=31536000; includeSubDomains; preload";
}
map $uri $datapulse_asset_cache {
    default "no-cache";
    /index.html "no-cache, no-store, must-revalidate";
    ~^/api/ "no-store";
    "~*-[a-z0-9]{8,}\.(js|css|woff2?|ttf|svg|png|jpe?g|webp)$" "public, max-age=31536000, immutable";
    ~^/assets/ "public, max-age=604800";
    ~^/favicon\.(ico|svg)$ "public, max-age=86400";
}
map $status $datapulse_cache {
    default "no-store";
    200 $datapulse_asset_cache;
    304 $datapulse_asset_cache;
}
server {
    listen 8080;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
    server_tokens off;
    client_max_body_size 2m;

    gzip on;
    gzip_vary on;
    gzip_comp_level 5;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/javascript application/json application/geo+json image/svg+xml;

    include /etc/nginx/security-headers.conf;
    add_header Cache-Control $datapulse_cache always;
    add_header Strict-Transport-Security $datapulse_hsts always;

    # Use the container DNS (Docker bridge/Compose/Kubernetes), with deferred API lookup.
    resolver ${NGINX_LOCAL_RESOLVERS} valid=30s ipv6=off;
    set $backend_upstream "${BACKEND_URL}";
    location ^~ /api/ {
        proxy_pass $backend_upstream$request_uri;
        proxy_http_version 1.1;
        proxy_ssl_server_name on;
        proxy_ssl_verify on;
        proxy_ssl_trusted_certificate /etc/ssl/certs/ca-certificates.crt;
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Authorization $http_authorization;
        proxy_set_header If-Match $http_if_match;
        proxy_hide_header Cache-Control;
        proxy_buffering off;
        proxy_read_timeout 75s;
    }
    location = /index.html { try_files $uri =404; }
    # Missing assets must be 404, never a misleading HTML SPA response.
    location ~* \.(js|css|json|geojson|map|woff2?|ttf|png|jpe?g|gif|svg|ico|webp)$ {
        try_files $uri =404;
    }
    location / { try_files $uri $uri/ /index.html; }
}
```

## .github/workflows/frontend-ci.yml

```yaml
name: Frontend CI

on:
  push:
    branches: [main, feat/backend-datapulse]
    paths:
      [
        "frontend/**",
        ".github/workflows/frontend-ci.yml",
        ".gitattributes",
        "compose.yaml",
        "docs/SEGURIDAD_FRONTEND.md",
      ]
  pull_request:
    branches: [main, feat/backend-datapulse]
    paths:
      [
        "frontend/**",
        ".github/workflows/frontend-ci.yml",
        ".gitattributes",
        "compose.yaml",
        "docs/SEGURIDAD_FRONTEND.md",
      ]
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: frontend-ci-${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true

defaults:
  run:
    shell: bash
    working-directory: frontend

jobs:
  lint-and-check:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22.12.0"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci --no-audit --no-fund
      # No ESLint target exists. Check the existing strict TS projects and infrastructure syntax.
      - name: Strict TypeScript and infrastructure syntax
        run: |
          npx --no-install tsc -p tsconfig.app.json --noEmit
          npx --no-install tsc -p tsconfig.spec.json --noEmit
          node --check docker/configure-build.mjs
          node --check docker/finalize-index.mjs
          node --check docker/smoke-test.mjs
          node --check docker/upstream-fixture.mjs
          node --check docker/check-production.mjs
          node --check docker/check-source-security.mjs
          node docker/check-source-security.mjs
          sh -n docker/14-validate-backend.sh
          node --test docker/build-config.test.mjs docker/security-build.test.mjs
      - name: Audit production dependencies
        run: npm run audit:prod

  test:
    needs: lint-and-check
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22.12.0"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci --no-audit --no-fund
      - name: Karma and Jasmine with ChromeHeadless
        run: |
          CHROME_BIN=$(command -v google-chrome)
          export CHROME_BIN
          npm run test:ci

  build:
    needs: lint-and-check
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22.12.0"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci --no-audit --no-fund
      - run: npm run build -- --configuration=production
      - run: node docker/check-production.mjs
      - run: test -s dist/datapulse/browser/index.html
      - uses: actions/upload-artifact@v4
        with:
          name: frontend-dist
          path: frontend/dist/datapulse/browser
          retention-days: 7

  docker-build:
    needs: [test, build]
    runs-on: ubuntu-latest
    timeout-minutes: 25
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22.12.0"
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v6
        with:
          context: frontend
          push: false
          load: true
          tags: datapulse-frontend:${{ github.sha }}
          build-args: |
            API_URL=/api/
            CONFIGURATION=production
          cache-from: type=gha,scope=frontend
          cache-to: type=gha,scope=frontend,mode=max
      - name: Check the runtime and HTTP contract
        env:
          IMAGE: datapulse-frontend:${{ github.sha }}
        run: |
          trap 'docker rm -f datapulse-frontend-check datapulse-api-check >/dev/null 2>&1 || true; docker network rm datapulse-frontend-check >/dev/null 2>&1 || true' EXIT
          RUNTIME_UID=$(docker run --rm --entrypoint id "$IMAGE" -u)
          test "$RUNTIME_UID" -gt 0
          docker run --rm --entrypoint sh "$IMAGE" -c '! command -v node && ! command -v npm && test ! -d /app/node_modules'
          if docker run --rm -e BACKEND_URL=http://bad.example/path "$IMAGE" >/dev/null 2>&1; then
            echo 'Invalid backend origin was accepted'; exit 1
          fi
          INVALID_BACKEND_URL=$(printf 'http://backend:8000\ninvalid')
          if docker run --rm -e BACKEND_URL="$INVALID_BACKEND_URL" "$IMAGE" >/dev/null 2>&1; then
            echo 'Multiline backend origin was accepted'; exit 1
          fi
          docker network create datapulse-frontend-check
          NODE_IMAGE=$(awk '/^FROM node:/{print $2; exit}' Dockerfile)
          docker run -d --name datapulse-api-check --network datapulse-frontend-check --network-alias backend             -v "$PWD/docker/upstream-fixture.mjs:/fixture.mjs:ro" "$NODE_IMAGE" node /fixture.mjs
          docker run -d --name datapulse-frontend-check --network datapulse-frontend-check             --cap-drop ALL --security-opt no-new-privileges:true -p 127.0.0.1:18080:8080 "$IMAGE"
          for _ in $(seq 1 60); do
            if [ "$(docker inspect --format '{{.State.Health.Status}}' datapulse-frontend-check)" = healthy ]; then break; fi
            sleep 1
          done
          test "$(docker inspect --format '{{.State.Health.Status}}' datapulse-frontend-check)" = healthy
          docker exec datapulse-frontend-check nginx -t
          node docker/smoke-test.mjs http://127.0.0.1:18080
      - name: Scan the final image with Trivy
        # v0.36.0; immutable full SHA, not a mutable third-party tag.
        uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25
        with:
          version: v0.76.2
          image-ref: datapulse-frontend:${{ github.sha }}
          scanners: vuln
          severity: HIGH,CRITICAL
          ignore-unfixed: false
          exit-code: "1"
          format: json
          output: ${{ github.workspace }}/trivy-frontend.json
      - name: Upload image vulnerability report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: frontend-trivy
          path: trivy-frontend.json
          if-no-files-found: ignore
          retention-days: 7
```

## .github/dependabot.yml

```yaml
version: 2
updates:
  - package-ecosystem: npm
    directory: /frontend
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    groups:
      frontend-dependencies:
        patterns: ['*']
  # Native uv ecosystem updates pyproject.toml and uv.lock together.
  - package-ecosystem: uv
    directory: /
    schedule:
      interval: weekly
    groups:
      python-dependencies:
        patterns: ['*']
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
  - package-ecosystem: docker
    directories: [/, /frontend]
    schedule:
      interval: weekly
```

## frontend/src/app/core/auth/auth.service.ts

```typescript
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
```

## frontend/src/app/core/auth/auth-types.ts

```typescript
export interface CaptchaAnswer {
  captcha_key: string;
  captcha_answer: string;
}
export interface CaptchaChallenge {
  captcha_key: string;
  image_url: string;
}
export interface MfaPending {
  mfa_required: true;
}
export type LogoutReason = 'expired' | 'revoked' | 'manual' | 'role_changed';
```

## frontend/src/app/core/auth/auth.guards.ts

```typescript
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of, switchMap } from 'rxjs';
import { AuthService } from './auth.service';
export const authGuard: CanActivateFn = (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth
    .restore()
    .pipe(
      map((user) =>
        user ? true : router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } }),
      ),
    );
};
export const roleGuard: CanActivateFn = (route) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth
    .restore()
    .pipe(switchMap((user) => user ? auth.reloadProfile() : of(null)))
    .pipe(map((user) => {
      const roles = route.data?.['roles'];
      const allowed = Array.isArray(roles) ? !!user && roles.includes(user.rol) : auth.canWrite();
      return user && allowed ? true : router.createUrlTree(['/sin-permiso']);
    }), catchError(() => of(router.createUrlTree(['/login']))));
};
```

## frontend/src/app/core/http/api-base.service.ts

```typescript
import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { EMPTY, expand, Observable, reduce, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Page } from '../../shared/models/dto';

export type Query = Record<string, string | number | boolean | null | undefined>;
@Injectable({ providedIn: 'root' })
export class ApiBaseService {
  private readonly http = inject(HttpClient);
  readonly base = environment.apiUrl.replace(/\/?$/, '/');
  url(path: string): string {
    return this.base + path.replace(/^\//, '');
  }
  isApi(url: string): boolean {
    const base = new URL(this.base, globalThis.location.origin);
    const target = new URL(url, globalThis.location.origin);
    return base.origin === target.origin && target.pathname.startsWith(base.pathname);
  }
  captchaImageUrl(value: unknown): string | null {
    if (typeof value !== 'string') return null;
    try {
      const base = new URL(this.base, location.origin);
      const url = new URL(value, base);
      return ['http:', 'https:'].includes(url.protocol) && url.origin === base.origin &&
        !url.username && !url.password && !url.search && !url.hash &&
        /\/auth\/captcha-image\/image\/[a-f0-9]{40}\/$/.test(url.pathname) ? url.href : null;
    } catch { return null; }
  }
  captchaImage(value: unknown): Observable<Blob> {
    const url = this.captchaImageUrl(value);
    return url ? this.http.get(url, { responseType: 'blob' }) : throwError(() => new Error('Imagen inválida.'));
  }
  get<T>(path: string, query: Query = {}): Observable<T> {
    let params = new HttpParams();
    for (const [key, value] of Object.entries(query))
      if (value !== undefined && value !== null && value !== '')
        params = params.set(key, String(value));
    return this.http.get<T>(this.url(path), { params });
  }
  all<T>(path: string, query: Query = {}): Observable<T[]> {
    // Build numbered requests ourselves; never follow a foreign next URL with JWT.
    const page = (number: number) =>
      this.get<Page<T>>(path, { ...query, page_size: 500, page: number });
    return page(1).pipe(
      expand((response, index) => (response.next ? page(index + 2) : EMPTY)),
      reduce((records: T[], response) => records.concat(response.results), []),
    );
  }
  post<T>(path: string, data: unknown = {}): Observable<T> {
    return this.http.post<T>(this.url(path), data);
  }
  put<T>(path: string, data: unknown = {}): Observable<T> {
    return this.http.put<T>(this.url(path), data);
  }
  delete<T>(path: string, version: number): Observable<T> {
    return this.http.delete<T>(this.url(path), { headers: { 'If-Match': `"${version}"` } });
  }
  pdf(path: string): Observable<Blob> {
    return this.http.get(this.url(path), { responseType: 'blob' });
  }
}
```

## frontend/src/app/core/http/error-parser.ts

```typescript
import { HttpErrorResponse } from '@angular/common/http';
export function errorCode(error: unknown): string | null {
  if (!(error instanceof HttpErrorResponse)) return null;
  const body: unknown = error.error;
  if (!body || typeof body !== 'object' || !('error' in body)) return null;
  const envelope = body.error;
  return envelope && typeof envelope === 'object' && 'code' in envelope && typeof envelope.code === 'string'
    ? envelope.code : null;
}
export function retryAfterSeconds(error: unknown, now = Date.now()): number {
  if (!(error instanceof HttpErrorResponse)) return 0;
  const value = error.headers.get('Retry-After');
  if (!value) return 0;
  const seconds = /^\d+$/.test(value) ? Number(value) : Math.ceil((Date.parse(value) - now) / 1000);
  return Number.isFinite(seconds) ? Math.max(0, Math.ceil(seconds)) : 0;
}
export function publicAuthRequest(url: string): boolean {
  return /\/auth\/(?:login|register|refresh|captcha|captcha-image(?:\/.*)?|mfa\/verify-login)\/$/.test(new URL(url, location.origin).pathname);
}
export function errorMessage(error: unknown): string {
  if (!(error instanceof HttpErrorResponse)) return 'No se pudo completar la operación.';
  if (error.status === 0) return 'Sin conexión con el servidor. Revisa la red e intenta de nuevo.';
  if (error.status >= 500) return 'El servidor no pudo completar la operación. Intenta más tarde o contacta soporte.';
  const code = errorCode(error);
  if (code === 'captcha_required' || code === 'captcha_invalid') return 'Completa el reto de verificación para continuar.';
  const body = error.error as { error?: { message?: unknown } } | null;
  const statuses: Record<number, string> = {
    401: 'Tu sesión venció. Inicia sesión de nuevo.',
    403: 'No tienes permisos para esta acción.',
    404: 'No se encontró el recurso.',
    409: 'El portafolio cambió. Revisa los datos actualizados antes de reintentar.',
    429: 'Demasiadas solicitudes. Espera un momento antes de intentar de nuevo.',
  };
  if (error.status === 429) {
    const seconds = retryAfterSeconds(error);
    return seconds ? `Demasiadas solicitudes. Intenta de nuevo en ${seconds} segundos.` : statuses[429];
  }
  const message = body?.error?.message;
  // Never expose details, stack traces or token-bearing bodies, even in logs.
  if ([400, 409].includes(error.status) && typeof message === 'string' && message.trim()) return message.slice(0, 240);
  return statuses[error.status] ?? 'No se pudo completar la operación.';
}
```

## frontend/src/app/core/interceptors/jwt.interceptor.ts

```typescript
import { inject } from '@angular/core';
import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../auth/auth.service';
import { ApiBaseService } from '../http/api-base.service';
import { errorCode, publicAuthRequest } from '../http/error-parser';

export const jwtInterceptor: HttpInterceptorFn = (request, next) => {
  const auth = inject(AuthService);
  const api = inject(ApiBaseService);
  const sessionId = auth.sessionId;
  const protectedApi =
    api.isApi(request.url) && !publicAuthRequest(request.url);
  const authorized =
    protectedApi && auth.accessToken
      ? request.clone({ setHeaders: { Authorization: `Bearer ${auth.accessToken}` } })
      : request;
  return next(authorized).pipe(
    catchError((error) => {
      if (
        protectedApi &&
        error instanceof HttpErrorResponse &&
        error.status === 401 &&
        errorCode(error) !== 'session_requires_mfa' &&
        auth.sessionId === sessionId &&
        auth.hasRefresh
      ) {
        return auth
          .refresh()
          .pipe(
            switchMap((token) =>
              next(request.clone({ setHeaders: { Authorization: `Bearer ${token}` } })),
            ),
          );
      }
      return throwError(() => error);
    }),
  );
};
```

## frontend/src/app/core/interceptors/error.interceptor.ts

```typescript
import { inject } from '@angular/core';
import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { ApiBaseService } from '../http/api-base.service';
import { AuthService } from '../auth/auth.service';
import { NotificationService } from '../state/notification.service';
import { errorCode, errorMessage, publicAuthRequest } from '../http/error-parser';

export const errorInterceptor: HttpInterceptorFn = (request, next) => {
  const api = inject(ApiBaseService);
  const auth = inject(AuthService);
  const notification = inject(NotificationService);
  const router = inject(Router);
  const sessionId = auth.sessionId;
  return next(request).pipe(
    catchError((error: unknown) => {
      if (api.isApi(request.url) && auth.sessionId === sessionId) {
        const isLogin = publicAuthRequest(request.url) && !/\/auth\/refresh\/$/.test(request.url);
        if (error instanceof HttpErrorResponse && error.status === 401 && !isLogin) {
          const hadSession = !!auth.accessToken;
          auth.logout(errorCode(error) === 'session_requires_mfa' ? 'role_changed' : 'expired');
          if (hadSession) {
            notification.show('Tu sesión venció. Inicia sesión de nuevo.');
            const navigation = router.getCurrentNavigation();
            const returnUrl =
              (navigation?.finalUrl ?? navigation?.extractedUrl)?.toString() ?? router.url;
            void router.navigate(['/login'], { queryParams: { returnUrl } });
          }
        } else notification.show(errorMessage(error));
      }
      return throwError(() => error);
    }),
  );
};
```

## frontend/src/app/features/auth/auth-page.ts

```typescript
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
```

## frontend/src/app/features/portafolios/routes.ts

```typescript
import { Routes } from '@angular/router';
import { roleGuard } from '../../core/auth/auth.guards';
export const routes: Routes = [
  { path: '', loadComponent: () => import('./portfolio-list').then((m) => m.PortfolioList) },
  {
    path: 'nuevo',
    data: { roles: ['ADMIN', 'ANALISTA'] },
    canActivate: [roleGuard],
    loadComponent: () => import('./portfolio-form').then((m) => m.PortfolioForm),
  },
  {
    path: ':id/editar',
    data: { roles: ['ADMIN', 'ANALISTA'] },
    canActivate: [roleGuard],
    loadComponent: () => import('./portfolio-form').then((m) => m.PortfolioForm),
  },
  {
    path: ':id',
    loadComponent: () => import('./portfolio-detail').then((m) => m.PortfolioDetailPage),
  },
];
```

## frontend/src/main.ts

```typescript
import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';

bootstrapApplication(App, appConfig).catch(() => console.error('No se pudo iniciar DataPulse.'));
```

## frontend/src/app/core/auth/auth-security.spec.ts

```typescript
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { AuthService } from './auth.service';

describe('Integridad de sesión y MFA', () => {
  let auth: AuthService;
  let http: HttpTestingController;
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    auth = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => { http.verify(); localStorage.clear(); });
  it('persiste ambas claves explícitas y limpia ambas al salir', () => {
    auth.setTokens({ access: 'access', refresh: 'refresh' });
    expect(localStorage.getItem('datapulse.auth.access')).toBe('access');
    expect(localStorage.getItem('datapulse.auth.refresh')).toBe('refresh');
    auth.logout('manual');
    expect(localStorage.getItem('datapulse.auth.access')).toBeNull();
    expect(localStorage.getItem('datapulse.auth.refresh')).toBeNull();
  });
  it('un logout remoto invalida el refresh en vuelo sin escribir de nuevo en storage', () => {
    auth.setTokens({ access: 'old', refresh: 'refresh' });
    auth.refresh().subscribe({ error: () => undefined });
    const pending = http.expectOne('/api/auth/refresh/');
    localStorage.removeItem('datapulse.auth.access');
    const remove = spyOn(localStorage, 'removeItem').and.callThrough();
    window.dispatchEvent(new StorageEvent('storage', { key: 'datapulse.auth.access', newValue: null }));
    pending.flush({ access: 'late' });
    expect(auth.accessToken).toBeNull();
    expect(auth.user).toBeNull();
    expect(remove).not.toHaveBeenCalled();
  });
  it('conserva los tokens ante indisponibilidad temporal del perfil', () => {
    auth.setTokens({ access: 'access', refresh: 'refresh' });
    auth.restore().subscribe();
    http.expectOne('/api/auth/me/').flush({}, { status: 503, statusText: 'Unavailable' });
    expect(auth.accessToken).toBe('access');
    expect(auth.user).toBeNull();
  });
  it('un reto MFA no almacena tokens y verifica con el contrato real code', () => {
    auth.login('admin@test.com', 'password').subscribe();
    http.expectOne('/api/auth/login/').flush({ mfa_required: true, mfa_token: 'ephemeral' });
    expect(auth.accessToken).toBeNull();
    expect(localStorage.getItem('datapulse.auth.access')).toBeNull();
    auth.verifyMfa('123456').subscribe();
    const verify = http.expectOne('/api/auth/mfa/verify-login/');
    expect(verify.request.body).toEqual({ mfa_token: 'ephemeral', code: '123456' });
    verify.flush({ access: 'access', refresh: 'refresh' });
    http.expectOne('/api/auth/me/').flush({ id: 1, rol: 'ADMIN' });
    expect(auth.hasRole('ADMIN')).toBeTrue();
    expect(JSON.stringify(localStorage)).not.toContain('ephemeral');
  });
  it('no revive una verificación MFA tardía tras logout', () => {
    auth.login('admin@test.com', 'password').subscribe();
    http.expectOne('/api/auth/login/').flush({ mfa_required: true, mfa_token: 'ephemeral' });
    auth.verifyMfa('123456').subscribe({ error: () => undefined });
    const pending = http.expectOne('/api/auth/mfa/verify-login/');
    auth.logout();
    pending.flush({ access: 'late', refresh: 'late-refresh' });
    expect(auth.accessToken).toBeNull();
  });
  it('rechaza una respuesta que no contiene ni JWT ni reto MFA válido', () => {
    auth.login('admin@test.com', 'password').subscribe({ error: () => undefined });
    http.expectOne('/api/auth/login/').flush({ mfa_required: true });
    expect(auth.accessToken).toBeNull();
  });
  it('actualiza permisos exclusivamente al volver a consultar me', () => {
    auth.login('admin@test.com', 'password').subscribe();
    http.expectOne('/api/auth/login/').flush({ access: 'access', refresh: 'refresh' });
    http.expectOne('/api/auth/me/').flush({ id: 1, rol: 'ADMIN' });
    auth.reloadProfile().subscribe();
    http.expectOne('/api/auth/me/').flush({ id: 1, rol: 'VIEWER' });
    expect(auth.hasRole('ADMIN')).toBeFalse();
    expect(auth.canWrite()).toBeFalse();
  });
});
```

## frontend/src/app/core/auth/role-security.spec.ts

```typescript
import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, provideRouter, RouterStateSnapshot, UrlTree } from '@angular/router';
import { firstValueFrom, Observable, of } from 'rxjs';
import { AuthService } from './auth.service';
import { roleGuard } from './auth.guards';
import { routes } from '../../features/portafolios/routes';

describe('Roles desde perfil de servidor', () => {
  for (const role of ['VIEWER', 'ANALISTA', 'ADMIN'] as const) {
    it(`${role}: aplica la lista de roles de la ruta de escritura`, async () => {
      TestBed.configureTestingModule({ providers: [provideRouter([]), { provide: AuthService,
        useValue: { restore: () => of({ id: 1, rol: role }), reloadProfile: () => of({ id: 1, rol: role }) } }] });
      const route = { data: { roles: ['ADMIN', 'ANALISTA'] } } as unknown as ActivatedRouteSnapshot;
      const result = TestBed.runInInjectionContext(() => roleGuard(route,
        { url: '/portafolios/nuevo' } as RouterStateSnapshot)) as Observable<boolean | UrlTree>;
      const decision = await firstValueFrom(result);
      if (role === 'VIEWER') expect(decision).toBeInstanceOf(UrlTree);
      else expect(decision).toBeTrue();
    });
  }
  it('declara roles y guard en ambas rutas de escritura', () => {
    for (const path of ['nuevo', ':id/editar']) {
      const route = routes.find((item) => item.path === path);
      expect(route?.canActivate).toContain(roleGuard);
      expect(route?.data?.['roles']).toEqual(['ADMIN', 'ANALISTA']);
    }
  });
});
```

## frontend/src/app/core/interceptors/security-interceptors.spec.ts

```typescript
import { TestBed } from '@angular/core/testing';
import { HttpClient, HttpErrorResponse, HttpHeaders, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { AuthService } from '../auth/auth.service';
import { jwtInterceptor } from './jwt.interceptor';
import { errorInterceptor } from './error.interceptor';
import { NotificationService } from '../state/notification.service';
import { errorMessage, retryAfterSeconds } from '../http/error-parser';

describe('Errores y frontera JWT de seguridad', () => {
  let http: HttpClient;
  let controller: HttpTestingController;
  let auth: AuthService;
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ providers: [provideRouter([]),
      provideHttpClient(withInterceptors([errorInterceptor, jwtInterceptor])), provideHttpClientTesting(),
      { provide: NotificationService, useValue: { show: () => undefined } }] });
    http = TestBed.inject(HttpClient);
    controller = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(AuthService);
    spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
  });
  afterEach(() => { controller.verify(); localStorage.clear(); });
  it('no filtra secretos ni details en errores 500', () => {
    const error = new HttpErrorResponse({ status: 500, error: { error: {
      message: 'secret-token', details: { traceback: 'database-password' } } } });
    expect(errorMessage(error)).not.toContain('secret-token');
    expect(errorMessage(error)).not.toContain('database-password');
  });
  it('interpreta Retry-After en segundos y fecha HTTP', () => {
    const error = new HttpErrorResponse({ status: 429, headers: new HttpHeaders({ 'Retry-After': '900' }) });
    expect(retryAfterSeconds(error)).toBe(900);
    expect(errorMessage(error)).toContain('900 segundos');
    expect(retryAfterSeconds(new HttpErrorResponse({ status: 429,
      headers: new HttpHeaders({ 'Retry-After': 'Wed, 18 Nov 2026 20:00:30 GMT' }) }), Date.parse('2026-11-18T20:00:00Z'))).toBe(30);
  });
  it('CAPTCHA y MFA públicos no llevan JWT y un MFA inválido no borra otra sesión', () => {
    auth.setTokens({ access: 'access', refresh: 'refresh' });
    http.get('/api/auth/captcha/').subscribe();
    const captcha = controller.expectOne('/api/auth/captcha/');
    expect(captcha.request.headers.has('Authorization')).toBeFalse();
    captcha.flush({});
    http.post('/api/auth/mfa/verify-login/', {}).subscribe({ error: () => undefined });
    const mfa = controller.expectOne('/api/auth/mfa/verify-login/');
    expect(mfa.request.headers.has('Authorization')).toBeFalse();
    mfa.flush({}, { status: 401, statusText: 'Unauthorized' });
    expect(auth.accessToken).toBe('access');
  });
  it('no retira JWT de los endpoints protegidos de autenticación', () => {
    auth.setTokens({ access: 'access', refresh: 'refresh' });
    http.post('/api/auth/mfa/enroll/', {}).subscribe();
    const enroll = controller.expectOne('/api/auth/mfa/enroll/');
    expect(enroll.request.headers.get('Authorization')).toBe('Bearer access');
    enroll.flush({});
  });
  it('no reintenta un segundo 401 después de renovar', () => {
    auth.setTokens({ access: 'old', refresh: 'refresh' });
    http.get('/api/paises/').subscribe({ error: () => undefined });
    controller.expectOne('/api/paises/').flush({}, { status: 401, statusText: 'Unauthorized' });
    controller.expectOne('/api/auth/refresh/').flush({ access: 'new' });
    controller.expectOne('/api/paises/').flush({}, { status: 401, statusText: 'Unauthorized' });
    controller.expectNone('/api/auth/refresh/');
    expect(auth.accessToken).toBeNull();
  });
});
```

## frontend/src/app/features/auth/auth-page.spec.ts

```typescript
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ActivatedRoute, convertToParamMap, provideRouter, Router } from '@angular/router';
import { AuthPage } from './auth-page';
import { AuthService } from '../../core/auth/auth.service';

describe('Login reforzado con CAPTCHA/MFA', () => {
  let fixture: ComponentFixture<AuthPage>;
  let page: AuthPage;
  let http: HttpTestingController;
  let router: Router;
  const key = 'a'.repeat(40);
  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({ imports: [AuthPage], providers: [provideRouter([]),
      provideHttpClient(), provideHttpClientTesting(),
      { provide: ActivatedRoute, useValue: { snapshot: { data: {}, queryParamMap: convertToParamMap({}) } } }
    ] }).compileComponents();
    fixture = TestBed.createComponent(AuthPage);
    page = fixture.componentInstance;
    http = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    spyOn(router, 'navigateByUrl').and.resolveTo(true);
    page.form.patchValue({ email: 'admin@test.com', password: 'Strong-test-2026!' });
    fixture.detectChanges();
  });
  afterEach(() => { http.verify(); localStorage.clear(); });
  it('muestra el CAPTCHA requerido y reintenta con clave y respuesta', () => {
    page.submit();
    http.expectOne('/api/auth/login/').flush({ error: { code: 'captcha_required' } }, { status: 400, statusText: 'Bad Request' });
    http.expectOne('/api/auth/captcha/').flush({ captcha_key: key, image_url: `/api/auth/captcha-image/image/${key}/` });
    http.expectOne(`${location.origin}/api/auth/captcha-image/image/${key}/`).flush(new Blob(['PNG'], { type: 'image/png' }));
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('img').src).toMatch(/^blob:/);
    page.form.controls.captcha_answer.setValue('answer');
    page.submit();
    const login = http.expectOne('/api/auth/login/');
    expect(login.request.body.captcha_key).toBe(key);
    expect(login.request.body.captcha_answer).toBe('answer');
    login.flush({ access: 'access', refresh: 'refresh' });
    http.expectOne('/api/auth/me/').flush({ id: 1, rol: 'ADMIN' });
    expect(router.navigateByUrl).toHaveBeenCalledWith('/dashboard');
  });
  it('presenta MFA sin guardar el reto y completa autenticación mediante recovery', () => {
    page.submit();
    http.expectOne('/api/auth/login/').flush({ mfa_required: true, mfa_token: 'temporary' });
    fixture.detectChanges();
    expect(page.mfaRequired()).toBeTrue();
    expect(TestBed.inject(AuthService).accessToken).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Verificar identidad');
    expect(page.form.controls.password.value).toBe('');
    page.mfaForm.controls.code.setValue('b'.repeat(32));
    page.submitMfa();
    const verify = http.expectOne('/api/auth/mfa/verify-login/');
    expect(verify.request.body).toEqual({ mfa_token: 'temporary', code: 'b'.repeat(32) });
    verify.flush({ access: 'access', refresh: 'refresh' });
    http.expectOne('/api/auth/me/').flush({ id: 1, rol: 'ADMIN' });
    expect(router.navigateByUrl).toHaveBeenCalledWith('/dashboard');
    expect(page.mfaForm.controls.code.value).toBe('');
  });
  it('respeta Retry-After sin reenviar credenciales durante el bloqueo', fakeAsync(() => {
    page.submit();
    http.expectOne('/api/auth/login/').flush({}, { status: 429, statusText: 'Too Many Requests', headers: { 'Retry-After': '30' } });
    page.submit();
    http.expectNone('/api/auth/login/');
    expect(page.retrySeconds()).toBe(30);
    tick(30000);
    expect(page.retrySeconds()).toBe(0);
  }));
  it('rechaza imágenes CAPTCHA externas o esquemas ejecutables', () => {
    page.loadCaptcha();
    http.expectOne('/api/auth/captcha/').flush({ captcha_key: key, image_url: 'https://evil.test/steal' });
    expect(page.captchaImage()).toBe('');
    page.loadCaptcha();
    http.expectOne('/api/auth/captcha/').flush({ captcha_key: key, image_url: 'javascript:alert(1)' });
    expect(page.captchaImage()).toBe('');
  });
  it('no repite el registro si el login posterior exige otro CAPTCHA', () => {
    fixture.destroy();
    TestBed.inject(ActivatedRoute).snapshot.data['register'] = true;
    fixture = TestBed.createComponent(AuthPage);
    page = fixture.componentInstance;
    page.form.patchValue({ nombre_completo: 'Nuevo', email: 'new@test.com', password: 'Strong-test-2026!' });
    page.submit();
    http.expectOne('/api/auth/register/').flush({ error: { code: 'captcha_required' } }, { status: 400, statusText: 'Bad Request' });
    http.expectOne('/api/auth/captcha/').flush({ captcha_key: key, image_url: `/api/auth/captcha-image/image/${key}/` });
    http.expectOne(`${location.origin}/api/auth/captcha-image/image/${key}/`).flush(new Blob(['PNG'], { type: 'image/png' }));
    page.form.controls.captcha_answer.setValue('first');
    page.submit();
    http.expectOne('/api/auth/register/').flush({ id: 7, rol: 'ANALISTA' });
    http.expectOne('/api/auth/login/').flush({ error: { code: 'captcha_required' } }, { status: 400, statusText: 'Bad Request' });
    http.expectOne('/api/auth/captcha/').flush({ captcha_key: key, image_url: `/api/auth/captcha-image/image/${key}/` });
    http.expectOne(`${location.origin}/api/auth/captcha-image/image/${key}/`).flush(new Blob(['PNG'], { type: 'image/png' }));
    page.form.controls.captcha_answer.setValue('second');
    page.submit();
    http.expectNone('/api/auth/register/');
    http.expectOne('/api/auth/login/').flush({ access: 'access', refresh: 'refresh' });
    http.expectOne('/api/auth/me/').flush({ id: 7, rol: 'ANALISTA' });
    expect(router.navigateByUrl).toHaveBeenCalledWith('/dashboard');
  });
});
```

## frontend/src/app/features/portafolios/position-security.spec.ts

```typescript
import { TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { PositionForm } from './position-form';

describe('Contrato UTC y Decimal de posiciones', () => {
  const close = jasmine.createSpy('close');
  beforeEach(async () => {
    close.calls.reset();
    await TestBed.configureTestingModule({ imports: [PositionForm], providers: [
      { provide: MatDialogRef, useValue: { close } },
      { provide: MAT_DIALOG_DATA, useValue: { countries: [{ codigo_iso: 'CO', nombre: 'Colombia', moneda_codigo: 'COP' }],
        portfolio: { version: 3, posiciones: [] } } }
    ] }).compileComponents();
  });
  it('rechaza una fecha futura y no envía la posición', () => {
    const form = TestBed.createComponent(PositionForm).componentInstance;
    form.form.patchValue({ pais: 'CO', monto_inversion_usd: '1234.56', fecha_entrada: '2999-12-31' });
    form.submit();
    expect(form.form.controls.fecha_entrada.hasError('future')).toBeTrue();
    expect(close).not.toHaveBeenCalled();
  });
  it('conserva monto como string exacto y fecha como YYYY-MM-DD', () => {
    const form = TestBed.createComponent(PositionForm).componentInstance;
    form.form.patchValue({ pais: 'CO', monto_inversion_usd: '1234.50', fecha_entrada: '2020-01-02' });
    form.submit();
    expect(close).toHaveBeenCalledWith(jasmine.objectContaining({
      monto_inversion_usd: '1234.50', fecha_entrada: '2020-01-02', version: 3
    }));
  });
});
```

## frontend/src/app/shared/security/dom-sanitizer.spec.ts

```typescript
import { SecurityContext } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { DomSanitizer } from '@angular/platform-browser';
import { DatePipe } from '@angular/common';

describe('Defensas de representación Angular', () => {
  it('elimina scripts y handlers, neutraliza javascript y conserva marcado benigno', () => {
    const sanitizer = TestBed.inject(DomSanitizer);
    const html = sanitizer.sanitize(SecurityContext.HTML,
      '<script>alert(1)</script><img src="x" onerror="alert(1)"><a href="javascript:alert(1)">x</a><b>texto</b>') ?? '';
    expect(html).not.toContain('<script');
    expect(html).not.toContain('onerror');
    expect(html).not.toContain('href="javascript:');
    expect(html).toContain('<b>texto</b>');
  });
  it('representa timestamps en UTC explícita independientemente de la zona del navegador', () => {
    expect(new DatePipe('en-US').transform('2026-11-18T01:30:00-05:00', 'yyyy-MM-dd HH:mm', 'UTC'))
      .toBe('2026-11-18 06:30');
  });
});
```

## frontend/docker/configure-build.mjs

```javascript
import { writeFileSync } from 'node:fs';

const [input = '/api/', configuration = 'production'] = process.argv.slice(2);
if (configuration !== 'production')
  throw new Error('The runtime image requires CONFIGURATION=production (AOT and hashed assets).');
let apiUrl = input;
let connectOrigin = '';
if (input === '/api/') {
  // The local reverse proxy owns /api/. Other deployments use an absolute URL.
} else {
  const url = new URL(input);
  if (
    !['http:', 'https:'].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    !url.pathname.endsWith('/')
  ) {
    throw new Error(
      'API_URL must be /api/ or an HTTP(S) URL ending in /, without credentials, query or fragment.',
    );
  }
  apiUrl = url.href;
  connectOrigin = ' ' + url.origin;
}
writeFileSync(
  'src/environments/environment.prod.ts',
  `// Generated only inside the Docker builder. API_URL is public configuration.\nexport const environment = ${JSON.stringify({ production: true, apiUrl })};\n`,
);
const csp = `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: blob:; connect-src 'self'${connectOrigin}; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'; worker-src 'self' blob:`;
writeFileSync('docker/csp-policy.json', JSON.stringify(csp));
writeFileSync(
  'docker/security-headers.conf',
  [
    `add_header Content-Security-Policy "${csp}" always;`,
    'add_header X-Content-Type-Options "nosniff" always;',
    'add_header X-Frame-Options "DENY" always;',
    'add_header Referrer-Policy "strict-origin-when-cross-origin" always;',
    'add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;',
    'add_header Cross-Origin-Opener-Policy "same-origin" always;',
    'add_header Cross-Origin-Resource-Policy "same-origin" always;',
  ].join('\n') + '\n',
);
```

## frontend/docker/finalize-index.mjs

```javascript
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
const file = 'dist/datapulse/browser/index.html';
const source = readFileSync(file, 'utf8');
// Angular critical-CSS output uses an inline onload handler. A normal stylesheet
// link works with script-src self and does not require unsafe-inline scripts.
let html = source.replace(/<link\b[^>]*>/gi, (link) => {
  if (!/\brel="stylesheet"/i.test(link)) return link;
  return link
    .replace(/\s+onload="this\.media='all'"/i, '')
    .replace(/\s+media="print"/i, ' media="all"');
});
if (/\son[a-z]+=/i.test(html))
  throw new Error('Unexpected inline event handler in generated HTML; review CSP.');
for (const match of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi))
  if (match[1].trim()) throw new Error('Unexpected inline script in generated HTML; review CSP.');
// Meta is a fallback for static hosting. frame-ancestors is header-only.
const policy = existsSync('docker/csp-policy.json')
  ? JSON.parse(readFileSync('docker/csp-policy.json', 'utf8'))
  : "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; worker-src 'self' blob:";
const meta = `<meta http-equiv="Content-Security-Policy" content="${policy.replace(/;?\s*frame-ancestors[^;]*;?/g, ';').replaceAll('&', '&amp;').replaceAll('"', '&quot;')}">`;
html = html.replace(/<meta\b[^>]*http-equiv="Content-Security-Policy"[^>]*>/gi, '');
html = html.replace(/<head>/i, `<head>${meta}`);
writeFileSync(file, html);
```

## frontend/docker/check-source-security.mjs

```javascript
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import assert from 'node:assert/strict';
const forbidden = /\b(?:innerHTML|outerHTML|bypassSecurityTrust\w*)\b|\bdocument\.write\s*\(|\beval\s*\(|\bnew\s+Function\s*\(|\bconsole\.(?:log|debug|info|warn)\s*\(/;
function inspect(path) {
  for (const item of readdirSync(path, { withFileTypes: true })) {
    const file = join(path, item.name);
    if (item.isDirectory()) inspect(file);
    else if (/\.(?:ts|html)$/.test(file) && !file.endsWith('.spec.ts')) {
      assert.ok(!forbidden.test(readFileSync(file, 'utf8')), `Review forbidden DOM/logging primitive in ${file}`);
    }
  }
}
inspect(process.argv[2] ?? 'src');
console.log('Application source: no HTML bypass, executable strings or verbose console logging.');
```

## frontend/docker/check-production.mjs

```javascript
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import assert from 'node:assert/strict';
const root = 'dist/datapulse/browser';
function inspect(path) {
  for (const entry of readdirSync(path, { withFileTypes: true })) {
    const file = join(path, entry.name);
    if (entry.isDirectory()) inspect(file);
    else assert.ok(!file.endsWith('.map'), `Public source map: ${file}`);
  }
}
inspect(root);
const html = readFileSync(join(root, 'index.html'), 'utf8');
assert.match(html, /http-equiv="Content-Security-Policy"/);
assert.match(html, /script-src 'self';/);
assert.ok(!html.includes('unsafe-eval'));
assert.ok(!/\son[a-z]+=/i.test(html));
console.log('Production artifact: CSP present, no source maps or inline handlers.');
```

## frontend/docker/security-build.test.mjs

```javascript
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname, resolve, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
const scripts = dirname(fileURLToPath(import.meta.url));
function isolated(check) {
  const root = mkdtempSync(join(tmpdir(), 'datapulse-security-'));
  try {
    mkdirSync(join(root, 'src/environments'), { recursive: true });
    mkdirSync(join(root, 'docker'));
    mkdirSync(join(root, 'dist/datapulse/browser'), { recursive: true });
    writeFileSync(join(root, 'dist/datapulse/browser/index.html'), '<html><head></head><body><app-root></app-root></body></html>');
    check(root);
  } finally {
    assert.equal(dirname(resolve(root)), resolve(tmpdir()));
    assert.ok(basename(root).startsWith('datapulse-security-'));
    rmSync(root, { recursive: true, force: true });
  }
}
const run = (root, script, ...args) => spawnSync(process.execPath, [join(scripts, script), ...args], { cwd: root, encoding: 'utf8' });
test('meta fallback and HTTP policy agree on the exact configured API origin', () => isolated((root) => {
  assert.equal(run(root, 'configure-build.mjs', 'https://api.example.test/api/').status, 0);
  assert.equal(run(root, 'finalize-index.mjs').status, 0);
  const html = readFileSync(join(root, 'dist/datapulse/browser/index.html'), 'utf8');
  assert.match(html, /http-equiv="Content-Security-Policy"/);
  assert.match(html, /connect-src 'self' https:\/\/api.example.test;/);
  assert.ok(!html.includes('frame-ancestors'));
  assert.ok(!html.includes('unsafe-eval'));
  const headers = readFileSync(join(root, 'docker/security-headers.conf'), 'utf8');
  assert.match(headers, /frame-ancestors 'none'/);
  assert.match(headers, /Cross-Origin-Resource-Policy "same-origin"/);
  assert.equal(run(root, 'check-production.mjs').status, 0);
}));
test('production gate rejects an accidentally published source map', () => isolated((root) => {
  run(root, 'finalize-index.mjs');
  writeFileSync(join(root, 'dist/datapulse/browser/main.js.map'), '{}');
  assert.notEqual(run(root, 'check-production.mjs').status, 0);
}));
test('source guard rejects a new unsafe DOM sink or verbose log in application code', () => isolated((root) => {
  writeFileSync(join(root, 'src/view.ts'), 'node.textContent = value;');
  assert.equal(run(root, 'check-source-security.mjs').status, 0);
  for (const source of ['node.innerHTML = value;', 'console.log(response);', 'new Function(input);']) {
    writeFileSync(join(root, 'src/view.ts'), source);
    assert.notEqual(run(root, 'check-source-security.mjs').status, 0);
  }
}));
```
