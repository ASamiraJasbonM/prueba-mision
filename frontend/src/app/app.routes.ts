import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth.guards';
export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./features/auth/auth-page').then((m) => m.AuthPage),
  },
  {
    path: 'registro',
    loadComponent: () => import('./features/auth/auth-page').then((m) => m.AuthPage),
    data: { register: true },
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./core/layout/shell').then((m) => m.Shell),
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      {
        path: 'dashboard',
        loadChildren: () => import('./features/dashboard/routes').then((m) => m.routes),
      },
      {
        path: 'paises',
        loadChildren: () => import('./features/paises/routes').then((m) => m.routes),
      },
      {
        path: 'portafolios',
        loadChildren: () => import('./features/portafolios/routes').then((m) => m.routes),
      },
      {
        path: 'alertas',
        loadChildren: () => import('./features/alertas/routes').then((m) => m.routes),
      },
      {
        path: 'sin-permiso',
        loadComponent: () => import('./shared/components/not-found').then((m) => m.NotFound),
        data: { forbidden: true },
      },
      {
        path: '**',
        loadComponent: () => import('./shared/components/not-found').then((m) => m.NotFound),
      },
    ],
  },
];
