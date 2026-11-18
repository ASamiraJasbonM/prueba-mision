import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { BehaviorSubject } from 'rxjs';
import { AuthService } from '../../core/auth/auth.service';
import { User } from '../../shared/models/dto';
import { AlertsStateService } from './alerts-state.service';
describe('AlertsStateService', () => {
  it('polls each 30 seconds only while authenticated and clears badge on logout', fakeAsync(() => {
    const users = new BehaviorSubject<User | null>(null);
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: { user$: users.asObservable() } },
      ],
    });
    const state = TestBed.inject(AlertsStateService);
    const http = TestBed.inject(HttpTestingController);
    let unread = -1;
    state.summary$.subscribe((s) => (unread = s.no_leidas));
    tick(30000);
    http.expectNone('/api/alertas/resumen/');
    users.next({ id: 1 } as User);
    tick(0);
    http
      .expectOne('/api/alertas/resumen/')
      .flush({ total: 3, no_leidas: 2, por_tipo: {}, por_severidad: {} });
    expect(unread).toBe(2);
    tick(30000);
    http
      .expectOne('/api/alertas/resumen/')
      .flush({ total: 3, no_leidas: 1, por_tipo: {}, por_severidad: {} });
    expect(unread).toBe(1);
    users.next(null);
    expect(unread).toBe(0);
    tick(60000);
    http.expectNone('/api/alertas/resumen/');
    TestBed.resetTestingModule();
    http.verify();
  }));
});
