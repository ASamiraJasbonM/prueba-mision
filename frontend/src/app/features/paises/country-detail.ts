import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { RiskQualityComponent } from '../../shared/components/risk-quality';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { FormBuilder } from '@angular/forms';
import { forkJoin, of, catchError, switchMap } from 'rxjs';
import { UiModule } from '../../shared/ui.module';
import { ApiBaseService } from '../../core/http/api-base.service';
import {
  CountryDetail,
  Indicator,
  ExchangeRate,
  RiskDetail,
  Risk,
  INDICATORS,
} from '../../shared/models/dto';
import { DecimalDisplayPipe } from '../../shared/pipes/decimal-display.pipe';
import { RiskBadgeComponent } from '../../shared/components/risk-badge.component';
import { StatusStateComponent } from '../../shared/components/status-state.component';
import { DataChart, ChartSeries } from '../../shared/components/data-chart';
import { chartNumber } from '../../shared/utils/decimal';
import { utcDaysAgo, utcToday } from '../../shared/utils/dates';
import { CountryFlag } from '../../shared/components/country-flag';
@Component({
  imports: [
    UiModule, DecimalDisplayPipe, RiskBadgeComponent, StatusStateComponent, DataChart, CountryFlag, RiskQualityComponent,
  ],
  template: `<a class="back-link" routerLink="/paises">← Explorar países</a>
    @if (country(); as c) {
      <div class="page-heading">
        <div>
          <p class="eyebrow">{{ c.region }} · {{ c.codigo_iso }}</p>
          <div class="country-title">
            <app-country-flag [code]="c.codigo_iso" [name]="c.nombre" />
            <h1>{{ c.nombre }}<span class="heading-dot">.</span></h1>
          </div>
          <p class="muted">
            {{ c.moneda_nombre }} ({{ c.moneda_codigo }}) · {{ c.poblacion | number }} habitantes
          </p>
        </div>
        <app-risk-badge [level]="risk()?.nivel_riesgo ?? null" />
      </div>
      <div class="indicator-grid">
        @for (i of indicators; track i.value) {
          <article class="kpi">
            <span>{{ i.label }}</span><strong>{{ latest(i.value)?.valor | decimalDisplay }}</strong>
            <p>{{ latest(i.value)?.unidad ?? 'Sin dato' }} · {{ latest(i.value)?.anio ?? '—' }}</p>
            <small>{{ latest(i.value)?.fuente ?? 'Fuente no disponible' }}</small>
          </article>
        }
      </div>
      <div class="detail-grid">
        <section class="panel">
          <div class="section-title">
            <div>
              <p class="eyebrow">CONTEXTO MACROECONÓMICO</p>
              <h2>Evolución de indicadores</h2>
            </div>
          </div>
          <form [formGroup]="form">
            <mat-form-field
              ><mat-label>Indicador</mat-label
              ><mat-select formControlName="tipo">
                @for (i of indicators; track i.value) {
                  <mat-option [value]="i.value">{{ i.label }}</mat-option>
                }
              </mat-select></mat-form-field
            >
          </form>
          <app-data-chart
            [labels]="years()"
            [series]="historySeries()"
            title="Indicador · últimos cinco años"
            xLabel="Año"
            [yLabel]="historySeries()[0]?.label ?? 'Valor'"
          />
          <p class="fine-print">Huecos = sin dato. {{ historySource() }}</p>
        </section>
        <section class="panel">
          <div class="section-title">
            <div>
              <p class="eyebrow">MERCADO CAMBIARIO</p>
              <h2>{{ c.moneda_codigo }} / USD</h2>
            </div>
            <span class="tag">30 días · UTC</span>
          </div>
          <app-data-chart
            [labels]="fxLabels()"
            [series]="fxSeries()"
            [title]="'USD por unidad de ' + c.moneda_codigo"
            xLabel="Fecha (UTC)"
            [yLabel]="'USD por 1 ' + c.moneda_codigo"
          />
          <p class="fine-print">
            USD por 1 {{ c.moneda_codigo }}. Última tasa:
            {{ lastRate()?.tasa | decimalDisplay: 12 }} · {{ lastRate()?.fuente ?? 'Sin dato' }}.
            Variación: {{ lastRate()?.variacion_porcentual | decimalDisplay }} %.
          </p>
        </section>
      </div>
      <section class="panel risk-detail">
        <div class="section-title">
          <div>
            <p class="eyebrow">ÍNDICE DE RIESGO PAÍS COMPUESTO</p>
            <h2>Una lectura del riesgo</h2>
          </div>
          @if (risk(); as r) {
            <span class="tag">{{ r.fecha_calculo | date: 'dd MMM yyyy HH:mm' : 'UTC' }} UTC</span>
          }
        </div>
        @if (risk(); as r) {
          <div class="risk-scores">
            <div>
              <span>IRPC</span><strong>{{ r.indice_compuesto | decimalDisplay }}</strong
              ><app-risk-badge [level]="r.nivel_riesgo" />
            </div>
            <div>
              <span>Económico</span><strong>{{ r.score_economico | decimalDisplay }}</strong>
            </div>
            <div>
              <span>Cambiario</span><strong>{{ r.score_cambiario | decimalDisplay }}</strong>
            </div>
            <div>
              <span>Estabilidad</span><strong>{{ r.score_estabilidad | decimalDisplay }}</strong>
            </div>
          </div>
          <p>
            Variación: {{ r.variacion | decimalDisplay }} · Tendencia:
            {{
              r.tendencia === 'SIN_HISTORICO'
                ? 'Sin histórico'
                : r.tendencia === 'SUBE'
                  ? 'Sube'
                  : r.tendencia === 'BAJA'
                    ? 'Baja'
                    : 'Estable'
            }}
          </p>
          @if (r.detalle_calculo.parcial) {
            <p class="notice">
              Cálculo parcial. Faltantes: {{ r.detalle_calculo.faltantes.join(', ') }}. Revisa la
              cobertura antes de comparar.
            </p>
          }
          <app-risk-quality [quality]="r.calidad_datos" />
          <details>
            <summary>Fuentes y factores del cálculo</summary>
            <div class="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Indicador</th>
                    <th>Valor</th>
                    <th>Fuente / año</th>
                    <th>Actualización UTC</th>
                  </tr>
                </thead>
                <tbody>
                  @for (source of r.detalle_calculo.fuentes | keyvalue; track source.key) {
                    <tr>
                      <td>{{ source.key }}</td>
                      <td>
                        {{ source.value.valor ?? source.value.valor_usd | decimalDisplay }}
                        {{ source.value.unidad ?? 'USD' }}
                      </td>
                      <td>{{ source.value.fuente }} · {{ source.value.anio }}</td>
                      <td>{{ source.value.fecha | date: 'dd MMM yyyy HH:mm' : 'UTC' }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
            <h3>Factores con penalización</h3>
            @for (factor of r.detalle_calculo.factores_en_riesgo; track factor.factor) {
              <p>
                {{ factor.factor }} · valor {{ factor.valor | decimalDisplay }} · penalización
                {{ factor.penalizacion | decimalDisplay }}
              </p>
            } @empty {
              <p class="muted">No hay factores penalizados registrados.</p>
            }
          </details>
          <h3>Histórico de riesgo</h3>
          <div class="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Fecha UTC</th>
                  <th>IRPC</th>
                  <th>Nivel</th>
                  <th>Cobertura</th>
                </tr>
              </thead>
              <tbody>
                @for (h of riskHistory(); track h.id) {
                  <tr>
                    <td>{{ h.fecha_calculo | date: 'dd MMM yyyy HH:mm' : 'UTC' }}</td>
                    <td>{{ h.indice_compuesto | decimalDisplay }}</td>
                    <td><app-risk-badge [level]="h.nivel_riesgo" /></td>
                    <td>{{ h.detalle_calculo.parcial ? 'Parcial' : 'Completa' }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        } @else {
          <app-status-state title="Este país aún no tiene un cálculo de riesgo" />
        }
      </section>
    } @else {
      <app-status-state
        [title]="error() ? 'País no disponible' : 'Cargando el contexto del país…'"
        [error]="error()"
        (retry)="load()"
      />
    }`,
  styles: [`
    .country-title { display: flex; align-items: center; gap: 16px; min-width: 0; }
    .country-title h1 { min-width: 0; overflow-wrap: anywhere; }
    app-country-flag { flex-shrink: 0; }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CountryDetailPage {
  private api = inject(ApiBaseService);
  private route = inject(ActivatedRoute);
  readonly country = signal<CountryDetail | null>(null);
  readonly risk = signal<RiskDetail | null>(null);
  readonly riskHistory = signal<Risk[]>([]);
  readonly error = signal(false);
  readonly indicators = INDICATORS;
  readonly form = inject(FormBuilder).nonNullable.group({ tipo: 'PIB' });
  readonly years = signal<string[]>([]);
  readonly historySeries = signal<ChartSeries[]>([]);
  readonly historySource = signal('');
  readonly fxLabels = signal<string[]>([]);
  readonly fxSeries = signal<ChartSeries[]>([]);
  readonly lastRate = signal<ExchangeRate | null>(null);
  private code = '';
  constructor() {
    this.route.paramMap.pipe(takeUntilDestroyed(inject(DestroyRef))).subscribe((p) => {
      this.code = p.get('codigo') ?? '';
      this.load();
    });
    this.form.valueChanges
      .pipe(takeUntilDestroyed(inject(DestroyRef)))
      .subscribe(() => this.updateHistory());
  }
  latest(type: string): Indicator | undefined {
    return this.country()
      ?.indicadores.filter((i) => i.tipo === type)
      .sort((a, b) => b.anio - a.anio)[0];
  }
  load(): void {
    this.country.set(null);
    this.error.set(false);
    forkJoin({
      country: this.api.get<CountryDetail>('paises/' + this.code + '/'),
      risk: this.api.get<RiskDetail>('riesgo/' + this.code + '/').pipe(
        catchError((e) => {
          if (e.status === 404) return of(null);
          throw e;
        }),
      ),
      history: this.api.all<Risk>('riesgo/' + this.code + '/historico/', {
        ordering: '-fecha_calculo',
      }),
      fx: this.api.all<ExchangeRate>('paises/' + this.code + '/tipo-cambio/', {
        fecha_desde: utcDaysAgo(29),
        fecha_hasta: utcToday(),
        ordering: 'fecha',
      }),
    }).subscribe({
      next: (r) => {
        this.country.set(r.country);
        this.risk.set(r.risk);
        this.riskHistory.set(r.history);
        this.lastRate.set(r.fx.at(-1) ?? null);
        const days = Array.from({ length: 30 }, (_, i) => utcDaysAgo(29 - i));
        this.fxLabels.set(days);
        this.fxSeries.set([
          {
            label: r.country.moneda_codigo + ' → USD',
            data: days.map((day) => chartNumber(r.fx.find((f) => f.fecha === day)?.tasa)),
          },
        ]);
        this.updateHistory();
      },
      error: () => this.error.set(true),
    });
  }
  private updateHistory(): void {
    const records =
      this.country()?.indicadores.filter((i) => i.tipo === this.form.controls.tipo.value) ?? [];
    const last = Math.max(new Date().getUTCFullYear() - 1, ...records.map((i) => i.anio));
    const years = Array.from({ length: 5 }, (_, i) => last - 4 + i);
    this.years.set(years.map(String));
    this.historySeries.set([
      {
        label: records[0]?.unidad ?? this.form.controls.tipo.value,
        data: years.map((y) => chartNumber(records.find((i) => i.anio === y)?.valor)),
      },
    ]);
    this.historySource.set(
      [...new Set(records.map((i) => i.fuente))].join(', ') || 'Fuente no disponible',
    );
  }
}
