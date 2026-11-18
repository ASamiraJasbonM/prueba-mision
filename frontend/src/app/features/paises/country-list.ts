import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder } from '@angular/forms';
import { debounceTime, startWith, switchMap, catchError, EMPTY } from 'rxjs';
import { UiModule } from '../../shared/ui.module';
import { ApiBaseService } from '../../core/http/api-base.service';
import { Country, Page } from '../../shared/models/dto';
import { StatusStateComponent } from '../../shared/components/status-state.component';
@Component({
  imports: [UiModule, StatusStateComponent],
  template: `<div class="page-heading">
      <div>
        <p class="eyebrow">DIEZ ECONOMÍAS, MUCHAS POSIBILIDADES</p>
        <h1>Explora la región<span class="heading-dot">.</span></h1>
        <p class="muted">Descubre los indicadores y el contexto de cada país.</p>
      </div>
      <span class="tag">{{ count() }} países</span>
    </div>
    <form class="filters panel" [formGroup]="filters">
      <mat-form-field class="search-field"
        ><mat-label>Buscar país o código</mat-label
        ><input matInput formControlName="search" placeholder="Colombia, CO…" /></mat-form-field
      ><mat-form-field
        ><mat-label>Región</mat-label
        ><mat-select formControlName="region"
          ><mat-option value="">Todas las regiones</mat-option>
          @for (region of regions(); track region) {
            <mat-option [value]="region">{{ region }}</mat-option>
          }
        </mat-select></mat-form-field
      >
    </form>
    @if (error()) {
      <app-status-state title="No pudimos cargar los países" [error]="true" (retry)="reload()" />
    }
    <div class="country-grid">
      @for (c of countries(); track c.codigo_iso) {
        <a class="country-card panel" [routerLink]="['/paises', c.codigo_iso]"
          ><div class="country-card-top">
            <span class="country-monogram">{{ c.codigo_iso }}</span><span aria-hidden="true"
              >↗</span
            >
          </div>
          <p class="eyebrow">{{ c.region }}</p>
          <h2>{{ c.nombre }}</h2>
          <div class="country-facts">
            <span
              >Moneda<strong>{{ c.moneda_codigo }}</strong></span
            ><span
              >Población<strong>{{ c.poblacion | number }}</strong></span
            >
          </div></a
        >
      } @empty {
        <app-status-state title="No hay países para esta búsqueda" />
      }
    </div>
    <mat-paginator
      [length]="count()"
      [pageIndex]="page()"
      [pageSize]="20"
      (page)="page.set($event.pageIndex); reload()"
      aria-label="Páginas de países"
    />`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CountryList {
  private api = inject(ApiBaseService);
  readonly filters = inject(FormBuilder).nonNullable.group({ search: '', region: '' });
  readonly countries = signal<Country[]>([]);
  readonly regions = signal<string[]>([]);
  readonly count = signal(0);
  readonly page = signal(0);
  readonly error = signal(false);
  constructor() {
    this.api.all<Country>('paises/').subscribe({
      next: (r) => this.regions.set([...new Set(r.map((c) => c.region))]),
      error: () => {},
    });
    this.filters.valueChanges
      .pipe(
        debounceTime(250),
        startWith(this.filters.getRawValue()),
        switchMap(() => {
          this.page.set(0);
          return this.request();
        }),
        takeUntilDestroyed(inject(DestroyRef)),
      )
      .subscribe((r) => this.set(r));
  }
  private request() {
    this.error.set(false);
    return this.api
      .get<Page<Country>>('paises/', {
        ...this.filters.getRawValue(),
        page: this.page() + 1,
        ordering: 'nombre',
      })
      .pipe(
        catchError(() => {
          this.error.set(true);
          return EMPTY;
        }),
      );
  }
  private set(r: Page<Country>): void {
    this.countries.set(r.results);
    this.count.set(r.count);
  }
  reload(): void {
    this.request().subscribe((r) => this.set(r));
  }
}
