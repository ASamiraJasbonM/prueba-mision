import { Pipe, PipeTransform } from '@angular/core';
import { formatDecimal } from '../utils/decimal';
@Pipe({ name: 'decimalDisplay' })
export class DecimalDisplayPipe implements PipeTransform {
  transform(value: string | null | undefined, digits = 2): string {
    return formatDecimal(value, digits);
  }
}
