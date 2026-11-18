import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder } from '@angular/forms';
import { debounceTime, startWith, switchMap, catchError, EMPTY } from 'rxjs';
import { UiModule } from '../../shared/ui.module';
import { ApiBaseService } from '../../core/http/api-base.service';
import { AuthService } from '../../core/auth/auth.service';
import { Portfolio } from '../../shared/models/dto';
import { StatusStateComponent } from '../../shared/components/status-state.component';
@Component({
  imports: [UiModule, StatusStateComponent],
  template: `<div class="page-heading">
      <div>
        <p class="eyebrow">TU ESTRATEGIA, EN UN SOLO LUGAR</p>
        <h1>Portafolios con perspectiva<span class="heading-dot">.</span></h1>
        <p class="muted">Organiza tus posiciones y entiende tu exposición regional.</p>
      </div>
      @if (auth.canWrite()) {
        <a mat-flat-button routerLink="nuevo">+ Crear portafolio</a>
      }
    </div>
    <form class="filters panel" [formGroup]="filters">
      <mat-form-field class="search-field"
        ><mat-label>Buscar portafolio</mat-label
        ><input matInput formControlName="search" /></mat-form-field
      ><mat-form-field
        ><mat-label>Visibilidad</mat-label
        ><mat-select formControlName="scope"
          ><mat-option value="own">Mis portafolios</mat-option
          ><mat-option value="public">Públicos de la comunidad</mat-option>
          @if (auth.user?.rol === 'ADMIN') {
            <mat-option value="all">Todos · administración</mat-option>
          }
        </mat-select></mat-form-field
      >
    </form>
    @if (error()) {
      <app-status-state
        title="No pudimos cargar los portafolios"
        [error]="true"
        (retry)="reload()"
      />
    }
    <div class="portfolio-grid">
      @for (p of visible().slice(page() * 12, page() * 12 + 12); track p.id) {
        <a class="portfolio-card panel" [routerLink]="[p.id]"
          ><div class="country-card-top">
            <span class="portfolio-symbol">▤</span
            ><span class="tag">{{ p.es_publico ? 'Público' : 'Privado' }}</span>
          </div>
          <h2>{{ p.nombre }}</h2>
          <p class="muted">{{ p.descripcion || 'Una estrategia por construir.' }}</p>
          <div class="card-footer">
            <span>Actualizado {{ p.fecha_modificacion | date: 'dd MMM yyyy' : 'UTC' }}</span
            ><span>Explorar ↗</span>
          </div></a
        >
      } @empty {
        <app-status-state
          title="Tu próxima estrategia empieza aquí"
          message="No hay portafolios para esta selección."
        />
      }
    </div>
    <mat-paginator
      [length]="visible().length"
      [pageIndex]="page()"
      [pageSize]="12"
      (page)="page.set($event.pageIndex)"
      aria-label="Páginas de portafolios"
    />`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PortfolioList {
  private api = inject(ApiBaseService);
  readonly auth = inject(AuthService);
  readonly filters = inject(FormBuilder).nonNullable.group({ search: '', scope: 'own' });
  readonly items = signal<Portfolio[]>([]);
  readonly scope = signal('own');
  readonly page = signal(0);
  readonly error = signal(false);
  readonly visible = computed(() =>
    this.items().filter((p) =>
      this.scope() === 'own'
        ? p.usuario === this.auth.user?.id
        : this.scope() === 'public'
          ? p.es_publico
          : true,
    ),
  );
  constructor() {
    this.filters.valueChanges
      .pipe(
        debounceTime(250),
        startWith(this.filters.getRawValue()),
        switchMap(() => {
          this.page.set(0);
          this.scope.set(this.filters.controls.scope.value);
          return this.request();
        }),
        takeUntilDestroyed(inject(DestroyRef)),
      )
      .subscribe((r) => this.items.set(r));
  }
  private request() {
    this.error.set(false);
    return this.api
      .all<Portfolio>('portafolios/', {
        search: this.filters.controls.search.value,
        ordering: '-fecha_modificacion',
      })
      .pipe(
        catchError(() => {
          this.error.set(true);
          return EMPTY;
        }),
      );
  }
  reload(): void {
    this.request().subscribe((r) => this.items.set(r));
  }
}
