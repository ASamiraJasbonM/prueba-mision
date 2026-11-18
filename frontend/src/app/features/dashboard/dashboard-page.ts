import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder } from '@angular/forms';
import { forkJoin, finalize, startWith, switchMap, catchError, EMPTY } from 'rxjs';
import { UiModule } from '../../shared/ui.module';
import { ApiBaseService } from '../../core/http/api-base.service';
import { AuthService } from '../../core/auth/auth.service';
import {
  DashboardSummary,
  MapCountry,
  INDICATORS,
  TrendPoint,
  Risk,
} from '../../shared/models/dto';
import { DecimalDisplayPipe } from '../../shared/pipes/decimal-display.pipe';
import { RiskBadgeComponent } from '../../shared/components/risk-badge.component';
import { StatusStateComponent } from '../../shared/components/status-state.component';
import { DataChart, ChartSeries } from '../../shared/components/data-chart';
import { MapLatam } from './map-latam';
import { chartNumber } from '../../shared/utils/decimal';
@Component({
  imports: [
    UiModule,
    DecimalDisplayPipe,
    RiskBadgeComponent,
    StatusStateComponent,
    DataChart,
    MapLatam,
  ],
  template: `<div class="page-heading">
      <div>
        <p class="eyebrow">EL PULSO DE LATINOAMÉRICA</p>
        <h1>Una región, en perspectiva<span class="heading-dot">.</span></h1>
        <p class="muted">Sigue los indicadores. Conecta las oportunidades.</p>
      </div>
      <span class="date-label">{{ today | date: 'dd MMMM yyyy' : 'UTC' }}</span>
    </div>
    @if (error()) {
      <app-status-state title="No pudimos cargar el panorama" [error]="true" (retry)="load()" />
    }
    @if (summary(); as s) {
      <div class="kpi-grid">
        <article class="kpi">
          <span>IRPC promedio regional</span
          ><strong>{{ s.promedio_irpc_region | decimalDisplay }}<small>/ 100</small></strong>
          <p>{{ s.paises_con_irpc }} de {{ s.total_paises }} países con cálculo</p>
        </article>
        <article class="kpi">
          <span>Economías en seguimiento</span
          ><strong>{{ s.total_paises | number: '2.0-0' }}</strong>
          <p>{{ s.paises_irpc_parcial }} con información parcial</p>
        </article>
        <article class="kpi">
          <span>Alertas activas</span><strong>{{ s.alertas_activas | number: '2.0-0' }}</strong
          ><a routerLink="/alertas">Explorar movimientos ↗</a>
        </article>
        <article class="kpi">
          <span>Tus portafolios</span><strong>{{ s.portafolios_usuario | number: '2.0-0' }}</strong
          ><a routerLink="/portafolios">Ver mis inversiones ↗</a>
        </article>
      </div>
      <div class="dashboard-grid">
        <section class="panel map-panel">
          <div class="section-title">
            <div>
              <p class="eyebrow">RIESGO PAÍS</p>
              <h2>El panorama regional</h2>
            </div>
            <span class="tag">Índice IRPC</span>
          </div>
          <app-map-latam [countries]="countries()" />
          <div class="risk-legend">
            <span><i class="low"></i>Bajo</span><span><i class="moderate"></i>Moderado</span
            ><span><i class="high"></i>Alto</span><span><i class="critical"></i>Crítico</span
            ><span><i></i>Sin cálculo</span>
          </div>
        </section>
        <section class="panel ranking">
          <div class="section-title">
            <div>
              <p class="eyebrow">DE MENOR A MAYOR RIESGO</p>
              <h2>Ranking regional</h2>
            </div>
            <a routerLink="/paises" aria-label="Explorar todos los países">↗</a>
          </div>
          <div class="table-scroll">
            <table
              mat-table
              [dataSource]="ranked()"
              matSort
              (matSortChange)="sort($event.direction)"
            >
              <ng-container matColumnDef="pais"
                ><th mat-header-cell *matHeaderCellDef>País</th>
                <td mat-cell *matCellDef="let c">
                  <a [routerLink]="['/paises', c.pais]"
                    ><span class="country-code">{{ c.pais }}</span
                    >{{ c.pais_nombre }}</a
                  >
                  @if (c.detalle_calculo.parcial) {
                    <small class="partial-label">Datos parciales</small>
                  }
                </td></ng-container
              ><ng-container matColumnDef="indice"
                ><th mat-header-cell *matHeaderCellDef mat-sort-header>IRPC</th>
                <td mat-cell *matCellDef="let c">
                  {{ c.indice_compuesto | decimalDisplay }}
                </td></ng-container
              ><ng-container matColumnDef="nivel"
                ><th mat-header-cell *matHeaderCellDef>Nivel</th>
                <td mat-cell *matCellDef="let c">
                  <app-risk-badge [level]="c.nivel_riesgo" /><small class="cell-secondary"
                    >{{ trendLabel(c.tendencia) }} · {{ c.variacion | decimalDisplay }}</small
                  >
                </td></ng-container
              >
              <tr mat-header-row *matHeaderRowDef="columns"></tr>
              <tr mat-row *matRowDef="let row; columns: columns"></tr>
            </table>
          </div>
        </section>
      </div>
      <section class="panel trends">
        <div class="section-title">
          <div>
            <p class="eyebrow">LA HISTORIA DETRÁS DEL DATO</p>
            <h2>Tendencias económicas</h2>
          </div>
          <span class="tag">Últimos 5 años</span>
        </div>
        <form [formGroup]="filters" class="filters">
          <mat-form-field
            ><mat-label>Indicador</mat-label
            ><mat-select formControlName="tipo">
              @for (i of indicators; track i.value) {
                <mat-option [value]="i.value">{{ i.label }}</mat-option>
              }
            </mat-select></mat-form-field
          ><mat-form-field
            ><mat-label>Comparar hasta 3 países</mat-label
            ><mat-select formControlName="paises" multiple>
              @for (c of countries(); track c.codigo_iso) {
                <mat-option
                  [value]="c.codigo_iso"
                  [disabled]="
                    filters.controls.paises.value.length >= 3 &&
                    !filters.controls.paises.value.includes(c.codigo_iso)
                  "
                  >{{ c.nombre }}</mat-option
                >
              }
            </mat-select></mat-form-field
          >
        </form>
        @if (trendError()) {
          <app-status-state
            title="No se pudieron cargar las tendencias"
            [error]="true"
            (retry)="refreshTrends()"
          />
        } @else if (filters.controls.paises.value.length) {
          <app-data-chart
            [title]="'Tendencias · ' + unit()"
            xLabel="Año"
            [yLabel]="unit()"
            [labels]="years()"
            [series]="series()"
          />
          <p class="fine-print">
            Unidad: {{ unit() }}. Los huecos indican datos no disponibles; cero representa un valor
            reportado. Fuentes: {{ sources() }}.
          </p>
        } @else {
          <p>Selecciona al menos un país para comparar.</p>
        }
      </section>
      @if (auth.user?.rol === 'ADMIN') {
        <section class="panel admin-actions">
          <div>
            <h3>Actualización de datos</h3>
            <p class="muted">Consulta fuentes y recalcula el riesgo regional.</p>
          </div>
          <button
            mat-stroked-button
            [disabled]="syncing()"
            (click)="sync('paises/sync-indicadores/')"
          >
            Sincronizar indicadores</button
          ><button mat-stroked-button [disabled]="syncing()" (click)="sync('riesgo/calcular/')">
            Recalcular riesgo
          </button>
          @if (report()) {
            <p role="status">{{ report() }}</p>
          }
        </section>
      }
    } @else if (!error()) {
      <app-status-state title="Construyendo el panorama…" />
    }`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DashboardPage {
  private api = inject(ApiBaseService);
  readonly auth = inject(AuthService);
  readonly summary = signal<DashboardSummary | null>(null);
  readonly countries = signal<MapCountry[]>([]);
  readonly ranked = signal<Risk[]>([]);
  readonly error = signal(false);
  readonly trendError = signal(false);
  readonly syncing = signal(false);
  readonly report = signal('');
  readonly today = new Date();
  readonly indicators = INDICATORS;
  readonly columns = ['pais', 'indice', 'nivel'];
  readonly years = signal<string[]>([]);
  readonly series = signal<ChartSeries[]>([]);
  readonly unit = signal('');
  readonly sources = signal('');
  readonly filters = inject(FormBuilder).nonNullable.group({
    tipo: 'PIB',
    paises: [['CO', 'BR', 'MX']],
  });
  constructor() {
    this.load();
    this.filters.valueChanges
      .pipe(
        startWith(this.filters.getRawValue()),
        switchMap(() => this.trends()),
        takeUntilDestroyed(inject(DestroyRef)),
      )
      .subscribe((points) => this.setTrends(points));
  }
  load(): void {
    this.summary.set(null);
    this.error.set(false);
    forkJoin({
      summary: this.api.get<DashboardSummary>('dashboard/resumen/'),
      countries: this.api.all<MapCountry>('dashboard/mapa/'),
      risks: this.api.all<Risk>('riesgo/', { ordering: '-indice_compuesto' }),
    }).subscribe({
      next: (r) => {
        this.summary.set(r.summary);
        this.countries.set(r.countries);
        this.risks = r.risks;
        this.sort('desc');
      },
      error: () => this.error.set(true),
    });
  }
  private risks: Risk[] = [];
  sort(direction: string): void {
    this.ranked.set(
      [...this.risks]
        .sort((a, b) => {
          const av = BigInt(a.indice_compuesto.replace('.', ''));
          const bv = BigInt(b.indice_compuesto.replace('.', ''));
          return (av < bv ? -1 : av > bv ? 1 : 0) * (direction === 'asc' ? 1 : -1);
        })
        .slice(0, 10),
    );
  }
  trendLabel(value: string): string {
    return (
      (
        {
          SUBE: '↑ Sube',
          BAJA: '↓ Baja',
          ESTABLE: 'Estable',
          SIN_HISTORICO: 'Sin histórico',
        } as Record<string, string>
      )[value] ?? value
    );
  }
  private trends() {
    this.trendError.set(false);
    const f = this.filters.getRawValue();
    if (!f.paises.length) {
      this.series.set([]);
      return EMPTY;
    }
    return this.api
      .all<TrendPoint>('dashboard/tendencias/', {
        tipo: f.tipo,
        paises: f.paises.slice(0, 3).join(','),
      })
      .pipe(
        catchError(() => {
          this.trendError.set(true);
          return EMPTY;
        }),
      );
  }
  refreshTrends(): void {
    this.trends().subscribe((points) => this.setTrends(points));
  }
  private setTrends(points: TrendPoint[]): void {
    const years = [...new Set(points.map((p) => p.anio))].sort();
    this.years.set(years.map(String));
    this.unit.set(points[0]?.unidad ?? 'Sin dato');
    this.sources.set(
      [...new Set(points.map((p) => p.fuente).filter(Boolean))].join(', ') || 'Sin fuente',
    );
    this.series.set(
      this.filters.controls.paises.value.map((code) => ({
        label: this.countries().find((c) => c.codigo_iso === code)?.nombre ?? code,
        data: years.map((y) =>
          chartNumber(points.find((p) => p.pais === code && p.anio === y)?.valor),
        ),
      })),
    );
  }
  sync(path: string): void {
    this.syncing.set(true);
    this.report.set('Actualizando…');
    this.api
      .post<Record<string, unknown>>(path)
      .pipe(finalize(() => this.syncing.set(false)))
      .subscribe({
        next: (r) => {
          const total = r['actualizados'] ?? r['calculados'] ?? 0;
          const errors = Array.isArray(r['errores']) ? r['errores'] : [];
          const detail = errors
            .map(
              (e: Record<string, unknown>) =>
                String(e['pais'] ?? 'Región') +
                ': ' +
                String(e['mensaje'] ?? e['error'] ?? 'No se pudo actualizar'),
            )
            .join(' · ');
          this.report.set(
            String(total) +
              ' registros actualizados. ' +
              (errors.length
                ? errors.length + ' errores parciales. ' + detail
                : 'Sin errores reportados.'),
          );
          this.load();
          this.refreshTrends();
        },
        error: () => this.report.set('La actualización no se completó. Intenta de nuevo.'),
      });
  }
}
