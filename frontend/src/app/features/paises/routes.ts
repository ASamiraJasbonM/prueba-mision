import { Routes } from '@angular/router';
export const routes: Routes = [
  { path: '', loadComponent: () => import('./country-list').then((m) => m.CountryList) },
  {
    path: ':codigo',
    loadComponent: () => import('./country-detail').then((m) => m.CountryDetailPage),
  },
];
