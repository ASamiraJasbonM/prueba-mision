import { inject } from '@angular/core';
import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../auth/auth.service';
import { ApiBaseService } from '../http/api-base.service';

export const jwtInterceptor: HttpInterceptorFn = (request, next) => {
  const auth = inject(AuthService);
  const api = inject(ApiBaseService);
  const sessionId = auth.sessionId;
  const protectedApi =
    api.isApi(request.url) && !/\/auth\/(login|register|refresh)\/$/.test(request.url);
  const authorized =
    protectedApi && auth.accessToken
      ? request.clone({ setHeaders: { Authorization: `Bearer ${auth.accessToken}` } })
      : request;
  return next(authorized).pipe(
    catchError((error) => {
      if (
        protectedApi &&
        error instanceof HttpErrorResponse &&
        error.status === 401 &&
        auth.sessionId === sessionId &&
        auth.hasRefresh
      ) {
        return auth
          .refresh()
          .pipe(
            switchMap((token) =>
              next(request.clone({ setHeaders: { Authorization: `Bearer ${token}` } })),
            ),
          );
      }
      return throwError(() => error);
    }),
  );
};
