import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, provideRouter, RouterStateSnapshot, UrlTree } from '@angular/router';
import { firstValueFrom, Observable, of } from 'rxjs';
import { AuthService } from './auth.service';
import { roleGuard } from './auth.guards';
import { routes } from '../../features/portafolios/routes';

describe('Roles desde perfil de servidor', () => {
  for (const role of ['VIEWER', 'ANALISTA', 'ADMIN'] as const) {
    it(`${role}: aplica la lista de roles de la ruta de escritura`, async () => {
      TestBed.configureTestingModule({ providers: [provideRouter([]), { provide: AuthService,
        useValue: { restore: () => of({ id: 1, rol: role }), reloadProfile: () => of({ id: 1, rol: role }) } }] });
      const route = { data: { roles: ['ADMIN', 'ANALISTA'] } } as unknown as ActivatedRouteSnapshot;
      const result = TestBed.runInInjectionContext(() => roleGuard(route,
        { url: '/portafolios/nuevo' } as RouterStateSnapshot)) as Observable<boolean | UrlTree>;
      const decision = await firstValueFrom(result);
      if (role === 'VIEWER') expect(decision).toBeInstanceOf(UrlTree);
      else expect(decision).toBeTrue();
    });
  }
  it('declara roles y guard en ambas rutas de escritura', () => {
    for (const path of ['nuevo', ':id/editar']) {
      const route = routes.find((item) => item.path === path);
      expect(route?.canActivate).toContain(roleGuard);
      expect(route?.data?.['roles']).toEqual(['ADMIN', 'ANALISTA']);
    }
  });
});
