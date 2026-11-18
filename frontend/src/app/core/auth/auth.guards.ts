import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs';
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
export const roleGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth
    .restore()
    .pipe(map((user) => (user && auth.canWrite() ? true : router.createUrlTree(['/sin-permiso']))));
};
