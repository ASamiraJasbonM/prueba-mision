import { Routes } from '@angular/router';
import { roleGuard } from '../../core/auth/auth.guards';
export const routes: Routes = [
  { path: '', loadComponent: () => import('./portfolio-list').then((m) => m.PortfolioList) },
  {
    path: 'nuevo',
    data: { roles: ['ADMIN', 'ANALISTA'] },
    canActivate: [roleGuard],
    loadComponent: () => import('./portfolio-form').then((m) => m.PortfolioForm),
  },
  {
    path: ':id/editar',
    data: { roles: ['ADMIN', 'ANALISTA'] },
    canActivate: [roleGuard],
    loadComponent: () => import('./portfolio-form').then((m) => m.PortfolioForm),
  },
  {
    path: ':id',
    loadComponent: () => import('./portfolio-detail').then((m) => m.PortfolioDetailPage),
  },
];
