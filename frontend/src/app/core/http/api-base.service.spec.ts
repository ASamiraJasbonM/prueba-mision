import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ApiBaseService } from './api-base.service';

describe('ApiBaseService', () => {
  let api: ApiBaseService;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(ApiBaseService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());
  it('recorre páginas sin seguir URLs externas ni perder registros', () => {
    let result: { id: number }[] = [];
    api.all<{ id: number }>('paises/').subscribe((value) => (result = value));
    http
      .expectOne('/api/paises/?page_size=500&page=1')
      .flush({ count: 2, next: 'https://ajeno.test/robar', previous: null, results: [{ id: 1 }] });
    http
      .expectOne('/api/paises/?page_size=500&page=2')
      .flush({ count: 2, next: null, previous: null, results: [{ id: 2 }] });
    expect(result).toEqual([{ id: 1 }, { id: 2 }]);
  });
});
