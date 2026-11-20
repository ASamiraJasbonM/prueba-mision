import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { UiModule } from '../../shared/ui.module';
import { AuthService } from '../../core/auth/auth.service';
import { ApiBaseService } from '../../core/http/api-base.service';
import { NotificationService } from '../../core/state/notification.service';
import { Country, Position, PositionInput } from '../../shared/models/dto';
import { DecimalDisplayPipe } from '../../shared/pipes/decimal-display.pipe';
import { DataChart } from '../../shared/components/data-chart';
import { StatusStateComponent } from '../../shared/components/status-state.component';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog.component';
import { PortfolioStateService } from './portfolio-state.service';
import { PositionForm } from './position-form';
import { chartNumber } from '../../shared/utils/decimal';
import { utcToday } from '../../shared/utils/dates';
@Component({
  imports: [UiModule, DecimalDisplayPipe, DataChart, StatusStateComponent],
  providers: [PortfolioStateService],
  template: `<a class="back-link" routerLink="/portafolios">← Mis portafolios</a>
    @if (state.detail(); as p) {
      <div class="page-heading">
        <div>
          <p class="eyebrow">
            {{ p.es_publico ? 'PORTAFOLIO PÚBLICO' : 'ESTRATEGIA PRIVADA' }} · VERSIÓN
            {{ p.version }}
          </p>
          <h1>{{ p.nombre }}<span class="heading-dot">.</span></h1>
          <p class="muted">{{ p.descripcion }}</p>
        </div>
        <div class="actions">
          <button mat-stroked-button (click)="pdf()" [disabled]="exporting()">
            {{ exporting() ? 'Preparando…' : '↓ Exportar PDF' }}
          </button>
          @if (auth.canEdit(p)) {
            <a mat-flat-button [routerLink]="['editar']" [disabled]="state.busy() || !state.fresh()"
              >Editar portafolio</a
            >
          }
        </div>
      </div>
      @if (!state.fresh() && !state.busy()) {
        <p class="notice" role="alert">
          Necesitamos releer la versión vigente antes de otra escritura.
          <button mat-button (click)="load()">Actualizar portafolio</button>
        </p>
      }
      @if (state.conflict()) {
        <p class="notice" role="alert">
          Otro usuario modificó el portafolio. Ya cargamos la versión vigente. Revisa los cambios y
          vuelve a realizar la operación.
        </p>
      }
      @if (error()) {
        <p class="error-text" role="alert">{{ error() }}</p>
      }
      <div class="kpi-grid">
        <article class="kpi">
          <span>Total invertido activo · USD</span
          ><strong class="money-total">{{
            p.metricas.total_invertido_usd | decimalDisplay
          }}</strong>
          <p>Importes de posiciones activas</p>
        </article>
        <article class="kpi">
          <span>Posiciones activas</span><strong>{{ p.metricas.posiciones_activas }}</strong>
          <p>En tu estrategia actual</p>
        </article>
        <article class="kpi">
          <span>Riesgo ponderado</span
          ><strong>{{ p.metricas.riesgo_promedio_ponderado | decimalDisplay }}</strong>
          <p>Sobre USD {{ p.metricas.monto_con_riesgo_usd | decimalDisplay }} con datos</p>
        </article>
        <article class="kpi">
          <span>Cobertura pendiente</span
          ><strong>{{ p.metricas.paises_con_datos_faltantes.length }}</strong>
          <p>
            {{ p.metricas.paises_con_datos_faltantes.join(', ') || 'Todos los países con datos' }}
          </p>
        </article>
      </div>
      <div class="detail-grid">
        <section class="panel">
          <div class="section-title">
            <h2>Distribución por país</h2>
            <span class="tag">USD</span>
          </div>
          @if (p.metricas.posiciones_activas) {
            <app-data-chart
              kind="pie"
              yLabel="USD"
              [labels]="countryLabels()"
              [series]="countrySeries()"
              title="Distribución de inversión por país"
              xLabel="País"
            />
          } @else {
            <app-status-state title="Tu estrategia aún no tiene posiciones" />
          }
        </section>
        <section class="panel">
          <div class="section-title">
            <h2>Composición por activo</h2>
            <span class="tag">USD</span>
          </div>
          @if (p.metricas.posiciones_activas) {
            <app-data-chart
              kind="doughnut"
              yLabel="USD"
              [labels]="assetLabels()"
              [series]="assetSeries()"
              title="Distribución por tipo de activo"
              xLabel="Tipo de activo"
            />
          } @else {
            <app-status-state title="Agrega tu primera posición" />
          }
        </section>
      </div>
      <section class="panel">
        <div class="section-title">
          <div>
            <p class="eyebrow">EL DETALLE DE TU ESTRATEGIA</p>
            <h2>Posiciones de inversión</h2>
          </div>
          @if (auth.canEdit(p)) {
            <button
              mat-flat-button
              (click)="position()"
              [disabled]="state.busy() || !state.fresh() || !countries().length"
            >
              + Agregar posición
            </button>
          }
        </div>
        <div class="table-scroll">
          <table mat-table [dataSource]="p.posiciones">
            <ng-container matColumnDef="pais"
              ><th mat-header-cell *matHeaderCellDef>País / Activo</th>
              <td mat-cell *matCellDef="let x">
                <a [routerLink]="['/paises', x.pais]">{{ countryName(x.pais) }}</a><small
                  class="cell-secondary"
                  >{{ x.tipo_activo }}</small
                >
              </td></ng-container
            ><ng-container matColumnDef="monto"
              ><th mat-header-cell *matHeaderCellDef>Inversión USD</th>
              <td mat-cell *matCellDef="let x">
                {{ x.monto_inversion_usd | decimalDisplay }}
              </td></ng-container
            ><ng-container matColumnDef="fechas"
              ><th mat-header-cell *matHeaderCellDef>Entrada / Salida UTC</th>
              <td mat-cell *matCellDef="let x">
                {{ x.fecha_entrada
                }}<small class="cell-secondary">{{ x.fecha_salida || '—' }}</small>
              </td></ng-container
            ><ng-container matColumnDef="estado"
              ><th mat-header-cell *matHeaderCellDef>Estado</th>
              <td mat-cell *matCellDef="let x">
                <span class="tag">{{ x.fecha_salida ? 'Cerrada' : 'Activa' }}</span><small
                  class="cell-secondary"
                  >{{ x.notas }}</small
                >
              </td></ng-container
            ><ng-container matColumnDef="acciones"
              ><th mat-header-cell *matHeaderCellDef>Acciones</th>
              <td mat-cell *matCellDef="let x">
                @if (auth.canEdit(p) && !x.fecha_salida) {
                  <button
                    mat-button
                    (click)="position(x)"
                    [disabled]="state.busy() || !state.fresh()"
                  >
                    Editar</button
                  ><button
                    mat-button
                    (click)="close(x)"
                    [disabled]="state.busy() || !state.fresh() || x.fecha_entrada >= today"
                    [matTooltip]="
                      x.fecha_entrada >= today
                        ? 'Disponible a partir del siguiente día UTC'
                        : 'Cerrar posición'
                    "
                  >
                    Cerrar
                  </button>
                } @else {
                  <span class="muted">Consulta</span>
                }
              </td></ng-container
            >
            <tr mat-header-row *matHeaderRowDef="columns"></tr>
            <tr mat-row *matRowDef="let row; columns: columns"></tr>
          </table>
          @if (!p.posiciones.length) {
            <app-status-state
              title="No hay posiciones todavía"
              message="Agrega una inversión para ver su distribución y riesgo."
            />
          }
        </div>
      </section>
      @if (auth.canEdit(p)) {
        <div class="danger-actions">
          <button mat-button [disabled]="state.busy() || !state.fresh()" (click)="remove()">
            Eliminar portafolio</button
          ><small>Las posiciones cerradas conservan su historial.</small>
        </div>
      }
    } @else {
      <app-status-state
        [title]="error() ? 'Portafolio no disponible' : 'Cargando portafolio…'"
        [error]="!!error()"
        (retry)="load()"
      />
    }`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PortfolioDetailPage {
  readonly state = inject(PortfolioStateService);
  readonly auth = inject(AuthService);
  private api = inject(ApiBaseService);
  private dialog = inject(MatDialog);
  private router = inject(Router);
  private notify = inject(NotificationService);
  private route = inject(ActivatedRoute);
  readonly error = signal('');
  readonly exporting = signal(false);
  readonly countries = signal<Country[]>([]);
  readonly today = utcToday();
  readonly columns = ['pais', 'monto', 'fechas', 'estado', 'acciones'];
  private id = 0;
  readonly countryLabels = computed(
    () => this.state.detail()?.metricas.por_pais.map((x) => this.countryName(x.codigo)) ?? [],
  );
  readonly countrySeries = computed(() => [
    {
      label: 'USD',
      data: this.state.detail()?.metricas.por_pais.map((x) => chartNumber(x.monto_usd)) ?? [],
    },
  ]);
  readonly assetLabels = computed(
    () =>
      this.state.detail()?.metricas.por_tipo_activo.map((x) => x.codigo.replaceAll('_', ' ')) ?? [],
  );
  readonly assetSeries = computed(() => [
    {
      label: 'USD',
      data:
        this.state.detail()?.metricas.por_tipo_activo.map((x) => chartNumber(x.monto_usd)) ?? [],
    },
  ]);
  constructor() {
    this.api
      .all<Country>('paises/')
      .subscribe({ next: (c) => this.countries.set(c), error: () => {} });
    this.route.paramMap.pipe(takeUntilDestroyed(inject(DestroyRef))).subscribe((p) => {
      this.id = Number(p.get('id'));
      this.load();
    });
  }
  countryName(code: string): string {
    return this.countries().find((c) => c.codigo_iso === code)?.nombre ?? code;
  }
  load(): void {
    this.error.set('');
    this.state.load(this.id).subscribe({
      error: () =>
        this.error.set('No se pudo cargar el portafolio. Reintenta o verifica tus permisos.'),
    });
  }
  position(position?: Position): void {
    const p = this.state.detail();
    if (!p || !this.auth.canEdit(p) || this.state.busy() || !this.state.fresh()) return;
    this.dialog
      .open(PositionForm, {
        width: '560px',
        maxWidth: '95vw',
        data: { portfolio: p, countries: this.countries(), position },
      })
      .afterClosed()
      .subscribe((input: PositionInput | undefined) => {
        if (input)
          this.state
            .position(this.id, input, position?.id)
            .subscribe({ next: () => this.notify.show('Posición guardada.'), error: () => {} });
      });
  }
  close(position: Position): void {
    const p = this.state.detail();
    if (
      !p ||
      !this.auth.canEdit(p) ||
      this.state.busy() ||
      !this.state.fresh() ||
      position.fecha_salida ||
      position.fecha_entrada >= utcToday()
    )
      return;
    this.confirm(
      'Cerrar posición',
      'La fecha de salida será hoy en UTC. La posición cerrada conserva su historial y no se puede editar.',
      'Cerrar posición',
      () =>
        this.state
          .close(this.id, position.id, this.state.detail()!.version)
          .subscribe({ next: () => this.notify.show('Posición cerrada.'), error: () => {} }),
    );
  }
  remove(): void {
    const p = this.state.detail();
    if (!p || !this.auth.canEdit(p) || this.state.busy() || !this.state.fresh()) return;
    this.confirm(
      'Eliminar portafolio',
      'El portafolio dejará de estar disponible. Confirma que deseas eliminarlo.',
      'Eliminar',
      () =>
        this.state
          .remove(this.id, this.state.detail()!.version)
          .subscribe({ next: () => void this.router.navigate(['/portafolios']), error: () => {} }),
    );
  }
  private confirm(title: string, message: string, action: string, callback: () => void): void {
    this.dialog
      .open(ConfirmDialogComponent, { data: { title, message, action }, width: '460px' })
      .afterClosed()
      .subscribe((confirmed) => {
        if (confirmed) callback();
      });
  }
  pdf(): void {
    if (this.exporting()) return;
    this.exporting.set(true);
    this.api.pdf('portafolios/' + this.id + '/export/pdf/').subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'DataPulse-portafolio-' + this.id + '.pdf';
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        this.exporting.set(false);
      },
      error: () => this.exporting.set(false),
    });
  }
}
