import { MatPaginatorIntl } from '@angular/material/paginator';
export function spanishPaginator(): MatPaginatorIntl {
  const p = new MatPaginatorIntl();
  p.itemsPerPageLabel = 'Elementos por página';
  p.nextPageLabel = 'Página siguiente';
  p.previousPageLabel = 'Página anterior';
  p.firstPageLabel = 'Primera página';
  p.lastPageLabel = 'Última página';
  p.getRangeLabel = (page, size, length) =>
    length === 0
      ? '0 de 0'
      : `${page * size + 1}–${Math.min((page + 1) * size, length)} de ${length}`;
  return p;
}
