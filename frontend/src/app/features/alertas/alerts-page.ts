import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder } from '@angular/forms';
import { debounceTime, finalize, timer, Subscription } from 'rxjs';
import { UiModule } from '../../shared/ui.module';
import { ApiBaseService } from '../../core/http/api-base.service';
import { Alert, Page } from '../../shared/models/dto';
import { AlertsStateService } from './alerts-state.service';
import { StatusStateComponent } from '../../shared/components/status-state.component';
@Component({
  imports: [UiModule, StatusStateComponent],
  template: `<div class="page-heading">
      <div>
        <p class="eyebrow">MANTENTE UN PASO ADELANTE</p>
        <h1>Centro de alertas<span class="heading-dot">.</span></h1>
        <p class="muted">Los movimientos que merecen tu atención.</p>
      </div>
      <button mat-stroked-button (click)="markAll()" [disabled]="busy()">
        Marcar todas como leídas
      </button>
    </div>
    @if (state.summary$ | async; as s) {
      <div class="metric-strip">
        <strong>{{ s.no_leidas }} <span>sin leer</span></strong
        ><strong>{{ s.total }} <span>alertas disponibles</span></strong
        ><span class="muted">Actualización cada 30 segundos</span>
      </div>
    }
    <form [formGroup]="filters" class="filters panel">
      <mat-form-field
        ><mat-label>Tipo de alerta</mat-label
        ><mat-select formControlName="tipo"
          ><mat-option value="">Todos</mat-option><mat-option value="RIESGO">Riesgo</mat-option
          ><mat-option value="TIPO_CAMBIO">Tipo de cambio</mat-option
          ><mat-option value="INDICADOR">Indicador</mat-option></mat-select
        ></mat-form-field
      ><mat-form-field
        ><mat-label>Severidad</mat-label
        ><mat-select formControlName="severidad"
          ><mat-option value="">Todas</mat-option><mat-option value="INFO">Informativa</mat-option
          ><mat-option value="WARNING">Advertencia</mat-option
          ><mat-option value="CRITICAL">Crítica</mat-option></mat-select
        ></mat-form-field
      ><mat-form-field
        ><mat-label>Estado</mat-label
        ><mat-select formControlName="leida"
          ><mat-option value="">Todas</mat-option><mat-option value="false">Sin leer</mat-option
          ><mat-option value="true">Leídas</mat-option></mat-select
        ></mat-form-field
      >
    </form>
    @if (error()) {
      <app-status-state title="No pudimos cargar las alertas" [error]="true" (retry)="load()" />
    } @else {
      <section class="panel alert-list" aria-label="Alertas">
        @for (alert of rows(); track alert.id) {
          <article class="alert-row" [class.unread]="!alert.leida">
            <span class="severity" [attr.data-severity]="alert.severidad">{{
              alert.severidad === 'CRITICAL' ? '!' : '◉'
            }}</span>
            <div>
              <div class="alert-meta">
                {{ alert.tipo_alerta }} · {{ alert.pais }} ·
                {{ alert.fecha_creacion | date: 'dd MMM yyyy, HH:mm' : 'UTC' }} UTC
              </div>
              <h3>{{ alert.titulo }}</h3>
              <p>{{ alert.mensaje }}</p>
              <a [routerLink]="['/paises', alert.pais]">Ver contexto del país ↗</a>
            </div>
            <button mat-button [disabled]="alert.leida || busy()" (click)="mark(alert.id)">
              {{ alert.leida ? 'Leída' : 'Marcar leída' }}
            </button>
          </article>
        } @empty {
          <app-status-state
            [title]="busy() ? 'Cargando alertas…' : 'Todo está al día'"
            message="No hay alertas para los filtros seleccionados."
          />
        }
        <mat-paginator
          [length]="count()"
          [pageIndex]="page()"
          [pageSize]="20"
          (page)="page.set($event.pageIndex); load()"
          aria-label="Páginas de alertas"
        />
      </section>
    }`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AlertsPage {
  readonly state = inject(AlertsStateService);
  private api = inject(ApiBaseService);
  readonly filters = inject(FormBuilder).nonNullable.group({ tipo: '', severidad: '', leida: '' });
  readonly rows = signal<Alert[]>([]);
  readonly count = signal(0);
  readonly page = signal(0);
  readonly busy = signal(false);
  readonly error = signal(false);
  private request?: Subscription;
  constructor() {
    this.filters.valueChanges
      .pipe(debounceTime(200), takeUntilDestroyed(inject(DestroyRef)))
      .subscribe(() => {
        this.page.set(0);
        this.load();
      });
    timer(30000, 30000)
      .pipe(takeUntilDestroyed(inject(DestroyRef)))
      .subscribe(() => this.load());
    inject(DestroyRef).onDestroy(() => this.request?.unsubscribe());
    this.load();
  }
  load(): void {
    this.request?.unsubscribe();
    this.busy.set(true);
    this.error.set(false);
    this.request = this.api
      .get<Page<Alert>>('alertas/', { ...this.filters.getRawValue(), page: this.page() + 1 })
      .pipe(finalize(() => this.busy.set(false)))
      .subscribe({
        next: (r) => {
          this.rows.set(r.results);
          this.count.set(r.count);
        },
        error: () => this.error.set(true),
      });
  }
  mark(id: number): void {
    this.busy.set(true);
    this.state
      .read(id)
      .pipe(finalize(() => this.busy.set(false)))
      .subscribe({
        next: () => {
          this.state.refresh();
          this.load();
        },
        error: () => {},
      });
  }
  markAll(): void {
    this.busy.set(true);
    this.state
      .readAll()
      .pipe(finalize(() => this.busy.set(false)))
      .subscribe({
        next: () => {
          this.state.refresh();
          this.load();
        },
        error: () => {},
      });
  }
}
