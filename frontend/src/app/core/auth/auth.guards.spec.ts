import { TestBed } from '@angular/core/testing';
import {
  ActivatedRouteSnapshot,
  provideRouter,
  RouterStateSnapshot,
  UrlTree,
} from '@angular/router';
import { Observable, of, firstValueFrom } from 'rxjs';
import { AuthService } from './auth.service';
import { authGuard, roleGuard } from './auth.guards';
describe('Guards', () => {
  it('redirects unauthenticated access and blocks VIEWER write routes', async () => {
    const auth = { restore: () => of(null), canWrite: () => false };
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: AuthService, useValue: auth }],
    });
    const route = {} as ActivatedRouteSnapshot;
    const state = { url: '/portafolios/nuevo' } as RouterStateSnapshot;
    const access = TestBed.runInInjectionContext(() => authGuard(route, state)) as Observable<
      boolean | UrlTree
    >;
    expect(await firstValueFrom(access)).toBeInstanceOf(UrlTree);
    const role = TestBed.runInInjectionContext(() => roleGuard(route, state)) as Observable<
      boolean | UrlTree
    >;
    expect(await firstValueFrom(role)).toBeInstanceOf(UrlTree);
  });
});
