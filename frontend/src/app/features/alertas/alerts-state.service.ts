import { DestroyRef, inject, Injectable } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { BehaviorSubject, catchError, EMPTY, of, switchMap, timer } from 'rxjs';
import { ApiBaseService } from '../../core/http/api-base.service';
import { AuthService } from '../../core/auth/auth.service';
import { AlertSummary } from '../../shared/models/dto';
const empty: AlertSummary = { total: 0, no_leidas: 0, por_tipo: {}, por_severidad: {} };
@Injectable({ providedIn: 'root' })
export class AlertsStateService {
  private readonly api = inject(ApiBaseService);
  private readonly summary = new BehaviorSubject<AlertSummary>(empty);
  readonly summary$ = this.summary.asObservable();
  constructor() {
    inject(AuthService)
      .user$.pipe(
        switchMap((user) =>
          user
            ? timer(0, 30000).pipe(
                switchMap(() =>
                  this.api.get<AlertSummary>('alertas/resumen/').pipe(catchError(() => EMPTY)),
                ),
              )
            : of(empty),
        ),
        takeUntilDestroyed(inject(DestroyRef)),
      )
      .subscribe((value) => this.summary.next(value));
  }
  refresh(): void {
    this.api
      .get<AlertSummary>('alertas/resumen/')
      .subscribe({ next: (value) => this.summary.next(value), error: () => {} });
  }
  read(id: number) {
    return this.api.put('alertas/' + id + '/leer/');
  }
  readAll() {
    return this.api.put('alertas/leer-todas/');
  }
}
