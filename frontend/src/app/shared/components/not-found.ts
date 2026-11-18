import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UiModule } from '../ui.module';
@Component({
  imports: [UiModule],
  template: `<section class="panel empty">
    <p class="eyebrow">
      {{ forbidden ? '403 · ACCESO RESTRINGIDO' : '404 · PÁGINA NO ENCONTRADA' }}
    </p>
    <h1>{{ forbidden ? 'Este espacio requiere otros permisos' : 'No encontramos esta página' }}</h1>
    <a mat-flat-button routerLink="/dashboard">Volver al panorama</a>
  </section>`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NotFound {
  readonly forbidden = inject(ActivatedRoute).snapshot.data['forbidden'];
}
