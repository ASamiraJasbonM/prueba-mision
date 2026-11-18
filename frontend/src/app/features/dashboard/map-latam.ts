import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  inject,
  input,
  OnDestroy,
  viewChild,
} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import type { FeatureCollection } from 'geojson';
import type { Map as LeafletMap } from 'leaflet';
import { MapCountry } from '../../shared/models/dto';
@Component({
  selector: 'app-map-latam',
  template: `<div
      #map
      class="region-map"
      role="region"
      aria-label="Mapa de riesgo en Latinoamérica"
    ></div>
    <p class="map-credit">Cartografía: Natural Earth · Selecciona un país para explorar</p>`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MapLatam implements AfterViewInit, OnDestroy {
  readonly countries = input<MapCountry[]>([]);
  private host = viewChild.required<ElementRef<HTMLDivElement>>('map');
  private http = inject(HttpClient);
  private router = inject(Router);
  private map?: LeafletMap;
  private disposed = false;
  async ngAfterViewInit(): Promise<void> {
    try {
      const [module, data] = await Promise.all([
        import('leaflet'),
        firstValueFrom(this.http.get<FeatureCollection>('assets/geojson/latam.geojson')),
      ]);
      if (this.disposed) return;
      // Vite exposes named exports; the production CommonJS chunk exposes default.
      const L = module.default ?? module;
      this.map = L.map(this.host().nativeElement, {
        scrollWheelZoom: false,
        attributionControl: false,
      }).setView([-16, -65], 3);
      const countriesLayer = L.geoJSON(data, {
        style: (f) => {
          const c = this.countries().find((c) => c.codigo_iso === f?.properties?.['codigo_iso']);
          return {
            color: '#f7faf5',
            weight: 1.5,
            fillColor: c?.color ?? '#cbd5cc',
            fillOpacity: 0.8,
          };
        },
        onEachFeature: (f, layer) => {
          const code = String(f.properties?.['codigo_iso']);
          const country = this.countries().find((c) => c.codigo_iso === code);
          const tip = document.createElement('span');
          tip.textContent =
            (country?.nombre ?? code) +
            ' · IRPC ' +
            (country?.indice_compuesto ?? 'sin dato') +
            (country?.parcial ? ' · parcial' : '');
          layer.bindTooltip(tip);
          layer.on('click', () => void this.router.navigate(['/paises', code]));
        },
      }).addTo(this.map);
      const fit = () => this.map?.fitBounds(countriesLayer.getBounds(), { padding: [18, 18] });
      fit();
      this.map.on('resize', fit);
    } catch {
      if (this.disposed) return;
      this.map?.remove();
      this.map = undefined;
      this.host().nativeElement.textContent = 'Mapa no disponible. Consulta el ranking de países.';
    }
  }
  ngOnDestroy(): void {
    this.disposed = true;
    this.map?.remove();
  }
}
