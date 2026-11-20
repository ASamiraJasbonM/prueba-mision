import { DestroyRef, Injectable, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Subject, Subscription, exhaustMap, interval, takeWhile } from 'rxjs';
import { ApiBaseService } from '../../core/http/api-base.service';
import { SyncJob } from '../../shared/models/dto';

const active = (job: SyncJob) => ['PENDIENTE', 'EJECUTANDO'].includes(job.estado);

@Injectable()
export class SyncStateService {
  private api = inject(ApiBaseService);
  private destroy = inject(DestroyRef);
  private poll?: Subscription;
  readonly job = signal<SyncJob | null>(null);
  readonly busy = signal(false);
  readonly error = signal('');
  readonly finished = new Subject<void>();

  start(): void {
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set('');
    this.api.post<SyncJob>('paises/sync-indicadores/').pipe(takeUntilDestroyed(this.destroy)).subscribe({
      next: job => this.watch(job),
      error: () => { this.busy.set(false); this.error.set('No se pudo solicitar la sincronización.'); },
    });
  }

  resume(): void {
    this.error.set('');
    this.api.get<SyncJob | null>('paises/sincronizaciones/').pipe(takeUntilDestroyed(this.destroy)).subscribe({
      next: job => { if (job) this.watch(job); },
      error: () => this.error.set('No se pudo consultar la ejecución. Reintenta consultar su estado.'),
    });
  }

  private watch(job: SyncJob): void {
    this.poll?.unsubscribe();
    this.accept(job);
    if (!active(job)) return;
    this.poll = interval(3000).pipe(
      exhaustMap(() => this.api.get<SyncJob>('paises/sincronizaciones/' + job.id + '/')),
      takeWhile(active, true), takeUntilDestroyed(this.destroy),
    ).subscribe({
      next: result => this.accept(result),
      error: () => this.error.set('Se interrumpió la consulta de estado. La ejecución continúa en el servidor.'),
    });
  }

  private accept(job: SyncJob): void {
    this.job.set(job);
    this.busy.set(active(job));
    if (!active(job)) this.finished.next();
  }
}
