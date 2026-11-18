import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
@Component({
  selector: 'app-status-state',
  imports: [MatButtonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div class="status-state" role="status">
    <div class="status-mark">{{ error() ? '!' : '—' }}</div>
    <h3>{{ title() }}</h3>
    <p>{{ message() }}</p>
    @if (error()) {
      <button mat-stroked-button (click)="retry.emit()">Intentar de nuevo</button>
    }
  </div>`,
})
export class StatusStateComponent {
  readonly title = input('Aún no hay datos');
  readonly message = input('Los datos aparecerán aquí cuando estén disponibles.');
  readonly error = input(false);
  readonly retry = output<void>();
}
