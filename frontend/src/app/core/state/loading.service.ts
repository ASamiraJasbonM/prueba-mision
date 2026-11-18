import { Injectable } from '@angular/core';
import { BehaviorSubject, distinctUntilChanged, map } from 'rxjs';
@Injectable({ providedIn: 'root' })
export class LoadingService {
  private readonly count = new BehaviorSubject(0);
  readonly loading$ = this.count.pipe(
    map((value) => value > 0),
    distinctUntilChanged(),
  );
  start(): void {
    this.count.next(this.count.value + 1);
  }
  stop(): void {
    this.count.next(Math.max(0, this.count.value - 1));
  }
}
