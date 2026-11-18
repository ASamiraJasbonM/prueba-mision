import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { EMPTY, expand, Observable, reduce } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Page } from '../../shared/models/dto';

export type Query = Record<string, string | number | boolean | null | undefined>;
@Injectable({ providedIn: 'root' })
export class ApiBaseService {
  private readonly http = inject(HttpClient);
  readonly base = environment.apiUrl.replace(/\/?$/, '/');
  url(path: string): string {
    return this.base + path.replace(/^\//, '');
  }
  isApi(url: string): boolean {
    const base = new URL(this.base, globalThis.location.origin);
    const target = new URL(url, globalThis.location.origin);
    return base.origin === target.origin && target.pathname.startsWith(base.pathname);
  }
  get<T>(path: string, query: Query = {}): Observable<T> {
    let params = new HttpParams();
    for (const [key, value] of Object.entries(query))
      if (value !== undefined && value !== null && value !== '')
        params = params.set(key, String(value));
    return this.http.get<T>(this.url(path), { params });
  }
  all<T>(path: string, query: Query = {}): Observable<T[]> {
    // Build numbered requests ourselves; never follow a foreign next URL with JWT.
    const page = (number: number) =>
      this.get<Page<T>>(path, { ...query, page_size: 500, page: number });
    return page(1).pipe(
      expand((response, index) => (response.next ? page(index + 2) : EMPTY)),
      reduce((records: T[], response) => records.concat(response.results), []),
    );
  }
  post<T>(path: string, data: unknown = {}): Observable<T> {
    return this.http.post<T>(this.url(path), data);
  }
  put<T>(path: string, data: unknown = {}): Observable<T> {
    return this.http.put<T>(this.url(path), data);
  }
  delete<T>(path: string, version: number): Observable<T> {
    return this.http.delete<T>(this.url(path), { headers: { 'If-Match': `"${version}"` } });
  }
  pdf(path: string): Observable<Blob> {
    return this.http.get(this.url(path), { responseType: 'blob' });
  }
}
