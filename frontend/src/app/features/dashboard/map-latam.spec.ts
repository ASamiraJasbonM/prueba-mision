import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { MapLatam } from './map-latam';
describe('MapLatam integration', () => {
  it('renders the actual lazy Leaflet module and colors API countries', async () => {
    await TestBed.configureTestingModule({
      imports: [MapLatam],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    const init = spyOn(MapLatam.prototype, 'ngAfterViewInit').and.callThrough();
    const fixture = TestBed.createComponent(MapLatam);
    fixture.componentRef.setInput('countries', [
      {
        codigo_iso: 'CO',
        nombre: 'Colombia',
        color: '#ef4444',
        indice_compuesto: '20.00',
        nivel_riesgo: 'CRITICO',
        parcial: false,
        latitud: '4.00',
        longitud: '-74.00',
      },
    ]);
    fixture.detectChanges();
    const http = TestBed.inject(HttpTestingController);
    http.expectOne('assets/geojson/latam.geojson').flush({
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { codigo_iso: 'CO' },
          geometry: {
            type: 'Polygon',
            coordinates: [
              [
                [-74, 4],
                [-73, 4],
                [-73, 5],
                [-74, 4],
              ],
            ],
          },
        },
      ],
    });
    await init.calls.mostRecent().returnValue;
    const polygon = fixture.nativeElement.querySelector('.region-map svg path') as SVGElement;
    expect(polygon)
      .withContext('Leaflet must render polygons in the production-style bundle')
      .not.toBeNull();
    expect(polygon?.getAttribute('fill')).toBe('#ef4444');
    expect(fixture.nativeElement.textContent).not.toContain('Mapa no disponible');
    http.verify();
    fixture.destroy();
  });
});
