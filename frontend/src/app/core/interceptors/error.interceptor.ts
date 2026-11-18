import { inject } from '@angular/core';
import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { ApiBaseService } from '../http/api-base.service';
import { AuthService } from '../auth/auth.service';
import { NotificationService } from '../state/notification.service';
import { errorCode, errorMessage, publicAuthRequest } from '../http/error-parser';

export const errorInterceptor: HttpInterceptorFn = (request, next) => {
  const api = inject(ApiBaseService);
  const auth = inject(AuthService);
  const notification = inject(NotificationService);
  const router = inject(Router);
  const sessionId = auth.sessionId;
  return next(request).pipe(
    catchError((error: unknown) => {
      if (api.isApi(request.url) && auth.sessionId === sessionId) {
        const isLogin = publicAuthRequest(request.url) && !/\/auth\/refresh\/$/.test(request.url);
        if (error instanceof HttpErrorResponse && error.status === 401 && !isLogin) {
          const hadSession = !!auth.accessToken;
          auth.logout(errorCode(error) === 'session_requires_mfa' ? 'role_changed' : 'expired');
          if (hadSession) {
            notification.show('Tu sesión venció. Inicia sesión de nuevo.');
            const navigation = router.getCurrentNavigation();
            const returnUrl =
              (navigation?.finalUrl ?? navigation?.extractedUrl)?.toString() ?? router.url;
            void router.navigate(['/login'], { queryParams: { returnUrl } });
          }
        } else notification.show(errorMessage(error));
      }
      return throwError(() => error);
    }),
  );
};
