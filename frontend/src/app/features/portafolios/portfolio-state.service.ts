import { inject, Injectable, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { catchError, finalize, Observable, switchMap, tap, throwError } from 'rxjs';
import { ApiBaseService } from '../../core/http/api-base.service';
import { PortfolioDetail, PortfolioInput, PositionInput } from '../../shared/models/dto';
@Injectable()
export class PortfolioStateService {
  private api = inject(ApiBaseService);
  readonly detail = signal<PortfolioDetail | null>(null);
  readonly busy = signal(false);
  readonly fresh = signal(false);
  readonly conflict = signal(false);
  load(id: number) {
    return this.api.get<PortfolioDetail>('portafolios/' + id + '/').pipe(
      tap((p) => {
        this.detail.set(p);
        this.fresh.set(true);
      }),
    );
  }
  update(id: number, input: PortfolioInput) {
    return this.write(id, this.api.put('portafolios/' + id + '/', input));
  }
  position(id: number, input: PositionInput, positionId?: number) {
    const path = 'portafolios/' + id + '/posiciones/' + (positionId ? positionId + '/' : '');
    return this.write(id, positionId ? this.api.put(path, input) : this.api.post(path, input));
  }
  close(id: number, positionId: number, version: number) {
    return this.write(
      id,
      this.api.delete('portafolios/' + id + '/posiciones/' + positionId + '/', version),
    );
  }
  remove(id: number, version: number) {
    this.busy.set(true);
    return this.api.delete('portafolios/' + id + '/', version).pipe(
      catchError((e) => this.recover(id, e)),
      finalize(() => this.busy.set(false)),
    );
  }
  private write(id: number, request: Observable<unknown>) {
    this.busy.set(true);
    this.conflict.set(false);
    return request.pipe(
      tap(() => this.fresh.set(false)),
      switchMap(() => this.load(id)),
      catchError((e) => this.recover(id, e)),
      finalize(() => this.busy.set(false)),
    );
  }
  private recover(id: number, error: HttpErrorResponse): Observable<never> {
    if (error.status !== 409) return throwError(() => error);
    this.conflict.set(true);
    this.fresh.set(false);
    return this.load(id).pipe(
      catchError(() => throwError(() => error)),
      switchMap(() => throwError(() => error)),
    );
  }
}
