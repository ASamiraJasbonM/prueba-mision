import { BreakpointObserver } from '@angular/cdk/layout';
import { toSignal } from '@angular/core/rxjs-interop';
import { map } from 'rxjs';
import { MatPaginatorIntl } from '@angular/material/paginator';
import { spanishPaginator } from './spanish-paginator';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { UiModule } from '../../shared/ui.module';
import { AuthService } from '../auth/auth.service';
import { LoadingService } from '../state/loading.service';
import { AlertsStateService } from '../../features/alertas/alerts-state.service';
@Component({
  imports: [UiModule, MatProgressBarModule],
  host: { '(document:keydown.escape)': 'menu.set(false)' },
  providers: [{ provide: MatPaginatorIntl, useFactory: spanishPaginator }],
  template: `<a class="skip-link" href="#main-content">Saltar al contenido</a>
    <div class="workspace">
      @if (menu() && compact()) {
        <button
          class="nav-backdrop"
          aria-label="Cerrar navegación"
          (click)="menu.set(false)"
        ></button>
      }
      <aside
        id="main-navigation"
        class="sidebar"
        [class.open]="menu()"
        [attr.inert]="compact() && !menu() ? '' : null"
      >
        <button
          mat-icon-button
          class="sidebar-close"
          aria-label="Cerrar navegación"
          (click)="menu.set(false)"
        >
          ×
        </button>
        <a class="brand" routerLink="/dashboard">D<span>◈</span> DataPulse<small>LATAM</small></a>
        <p class="nav-caption">ESPACIO DE TRABAJO</p>
        <nav aria-label="Navegación principal">
          @for (item of links; track item.path) {
            <a [routerLink]="item.path" routerLinkActive="active" (click)="menu.set(false)"
              ><span aria-hidden="true">{{ item.icon }}</span
              >{{ item.label }}
              @if (item.path === '/alertas' && (alerts.summary$ | async); as summary) {
                <b class="nav-badge">{{ summary.no_leidas }}</b>
              }
            </a>
          }
        </nav>
        <div class="sidebar-bottom">
          <div class="live-dot">Perspectiva regional</div>
          <p>Datos para entender.<br />Contexto para decidir.</p>
          <small>DATAPULSE LATAM © 2026</small>
        </div>
      </aside>
      <div class="workspace-main">
        <header class="topbar">
          <button
            mat-icon-button
            aria-label="Abrir navegación"
            aria-controls="main-navigation"
            [attr.aria-expanded]="menu()"
            class="menu-button"
            (click)="menu.set(!menu())"
          >
            ☰</button
          ><span class="top-context">INTELIGENCIA REGIONAL <span>/</span> LATINOAMÉRICA</span>
          <div class="account">
            <span class="avatar">{{ auth.user?.nombre_completo?.slice(0, 1) }}</span><span
              >{{ auth.user?.nombre_completo }}<small>{{ auth.user?.rol }}</small></span
            ><button mat-button (click)="logout()">Salir ↗</button>
          </div>
        </header>
        @if (loading.loading$ | async) {
          <mat-progress-bar mode="indeterminate" class="global-progress" />
        }
        <main id="main-content" class="content"><router-outlet /></main>
        <footer class="footer">DataPulse Latam <span>El contexto hace la diferencia.</span></footer>
      </div>
    </div>`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Shell {
  readonly auth = inject(AuthService);
  readonly loading = inject(LoadingService);
  readonly alerts = inject(AlertsStateService);
  private router = inject(Router);
  readonly menu = signal(false);
  readonly compact = toSignal(
    inject(BreakpointObserver)
      .observe('(max-width:1024px)')
      .pipe(map((state) => state.matches)),
    { initialValue: window.innerWidth <= 1024 },
  );
  readonly links = [
    { path: '/dashboard', label: 'Panorama general', icon: '◫' },
    { path: '/paises', label: 'Explorar países', icon: '◎' },
    { path: '/portafolios', label: 'Mis portafolios', icon: '▤' },
    { path: '/alertas', label: 'Centro de alertas', icon: '♧' },
  ];
  logout(): void {
    this.auth.logout();
    void this.router.navigate(['/login']);
  }
}
