import { Routes } from '@angular/router';
import { roleGuard } from '../../core/auth/auth.guards';
export const routes: Routes = [
  { path: '', loadComponent: () => import('./portfolio-list').then((m) => m.PortfolioList) },
  {
    path: 'nuevo',
    canActivate: [roleGuard],
    loadComponent: () => import('./portfolio-form').then((m) => m.PortfolioForm),
  },
  {
    path: ':id/editar',
    canActivate: [roleGuard],
    loadComponent: () => import('./portfolio-form').then((m) => m.PortfolioForm),
  },
  {
    path: ':id',
    loadComponent: () => import('./portfolio-detail').then((m) => m.PortfolioDetailPage),
  },
];
