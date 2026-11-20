import {
  ChangeDetectionStrategy, Component, computed, effect, input, signal,
} from '@angular/core';

const COUNTRIES = new Set(['CO', 'BR', 'MX', 'AR', 'CL', 'PE', 'EC', 'UY', 'PY', 'PA']);

@Component({
  selector: 'app-country-flag',
  template: `@if (source() && !failed()) {
    <img [src]="source()" [alt]="'Bandera de ' + name()" width="64" height="48"
      (error)="failed.set(true)" />
  } @else {
    <small class="muted">Bandera no disponible</small>
  }`,
  styles: ['img { display: block; border: 1px solid #dce4db; border-radius: 4px; object-fit: cover; }'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CountryFlag {
  readonly code = input('');
  readonly name = input('');
  readonly failed = signal(false);
  readonly source = computed(() => {
    const code = this.code().toUpperCase();
    return COUNTRIES.has(code) ? `/assets/flags/${code.toLowerCase()}.svg` : null;
  });
  constructor() {
    effect(() => {
      this.code();
      this.failed.set(false);
    });
  }
}
