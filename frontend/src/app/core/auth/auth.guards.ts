import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of, switchMap } from 'rxjs';
import { AuthService } from './auth.service';
export const authGuard: CanActivateFn = (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth
    .restore()
    .pipe(
      map((user) =>
        user ? true : router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } }),
      ),
    );
};
export const roleGuard: CanActivateFn = (route) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth
    .restore()
    .pipe(switchMap((user) => user ? auth.reloadProfile() : of(null)))
    .pipe(map((user) => {
      const roles = route.data?.['roles'];
      const allowed = Array.isArray(roles) ? !!user && roles.includes(user.rol) : auth.canWrite();
      return user && allowed ? true : router.createUrlTree(['/sin-permiso']);
    }), catchError(() => of(router.createUrlTree(['/login']))));
};
