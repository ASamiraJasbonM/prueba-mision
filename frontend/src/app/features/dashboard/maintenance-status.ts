import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { finalize, timer } from 'rxjs';
import { UiModule } from '../../shared/ui.module';
import { ApiBaseService } from '../../core/http/api-base.service';

interface Run {
  id: string;
  estado: string;
  iniciado: string;
  terminado: string | null;
  actualizados: number;
  errores: { pais?: string; operacion?: string; code?: string; causa?: string }[];
  cobertura?: { pais: string; externos: number; esperados: number; no_verificados?: number; faltantes: number; dias_consecutivos?: number }[];
  ejecucion_url: string | null;
}
interface Task { tarea: string; ultima_ejecucion: Run | null; ultimo_exito: Run | null; }

@Component({
  selector: 'app-maintenance-status',
  imports: [UiModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<section class="panel maintenance" aria-label="Mantenimiento programado">
    <h3>Mantenimiento programado</h3>
    <p class="muted">Estado registrado por los comandos de mantenimiento. Actualización cada minuto.</p>
    <button mat-stroked-button (click)="load()" [disabled]="busy()">Actualizar estado</button>
    @if (error()) { <p role="alert">No se pudo consultar el mantenimiento. Reintenta para obtener el estado vigente.</p> }
    @for (task of tasks(); track task.tarea) {
      <article>
        <h4>{{ label(task.tarea) }}</h4>
        @if (task.ultima_ejecucion; as run) {
          <p>Último intento: <strong>{{ run.estado }}</strong> · {{ run.iniciado | date:'dd/MM/yyyy HH:mm':'UTC' }} UTC.
            {{ run.actualizados }} registros actualizados.</p>
          @if (run.ejecucion_url) { <a [href]="run.ejecucion_url" target="_blank" rel="noopener noreferrer">Ver ejecución en GitHub</a> }
          @if (run.errores.length) {
            <p>{{ run.errores.length }} errores registrados; se conservan los datos anteriores.</p>
            @for (e of run.errores.slice(0, 5); track $index) {
              <p>{{ e.pais || 'General' }} · {{ e.operacion || task.tarea }} · {{ e.causa || e.code || 'Error de proveedor' }}</p>
            }
          }
          @if (run.cobertura?.length) {
            <details><summary>Cobertura externa al terminar el intento</summary>
              @for (country of run.cobertura; track country.pais) {
                <p>{{ country.pais }}: {{ country.externos }}/{{ country.esperados }} observaciones externas ·
                  {{ country.no_verificados ?? 0 }} no verificadas · {{ country.faltantes }}
                  {{ task.tarea === 'tipos_cambio' ? 'fechas sin tasa externa' : 'registros ausentes' }}.
                  @if (country.dias_consecutivos !== undefined) { {{ country.dias_consecutivos }} días externos consecutivos al ejecutar (UTC). }
                </p>
              }
            </details>
          }
        } @else { <p>Sin ejecuciones registradas. No se infiere éxito de la ausencia de historial.</p> }
        @if (task.ultimo_exito; as success) {
          <p>Último éxito: {{ success.terminado | date:'dd/MM/yyyy HH:mm':'UTC' }} UTC · {{ success.actualizados }} registros actualizados.</p>
        } @else { <p>Sin éxito registrado.</p> }
      </article>
    }
  </section>`,
  styles: [`article { padding: 12px 0; border-top: 1px solid #dfe5da; } .maintenance { margin-bottom: 24px; overflow-wrap: anywhere; }`],
})
export class MaintenanceStatus {
  private api = inject(ApiBaseService);
  private destroy = inject(DestroyRef);
  readonly tasks = signal<Task[]>([]);
  readonly busy = signal(false);
  readonly error = signal(false);
  constructor() {
    this.load();
    timer(60000, 60000).pipe(takeUntilDestroyed(this.destroy)).subscribe(() => this.load());
  }
  label(task: string): string {
    return ({ indicadores: 'Indicadores económicos', tipos_cambio: 'Tipos de cambio', paises: 'Datos de países' } as Record<string, string>)[task] ?? task;
  }
  load(): void {
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set(false);
    this.api.get<Task[]>('dashboard/mantenimiento/').pipe(
      takeUntilDestroyed(this.destroy), finalize(() => this.busy.set(false)),
    ).subscribe({ next: value => this.tasks.set(value), error: () => this.error.set(true) });
  }
}
