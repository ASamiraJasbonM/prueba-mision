/** Financial decisions stay in decimal strings/BigInt. Number is chart-only. */
export function normalizeMoney(value: string): string {
  const text = value.trim();
  return /^\d{1,3}(,\d{3})+(\.\d{1,2})?$/.test(text) ? text.replaceAll(',', '') : text;
}
/** Preserve incomplete input and cents; invalid precision is never rounded away. */
export function formatMoneyInput(value: string): string {
  const text = /^\d{1,3}(,\d{3})+(\.\d{0,2})?$/.test(value)
    ? value.replaceAll(',', '') : value;
  if (!/^\d+(\.\d{0,2})?$/.test(text)) return value;
  const [integer, fraction] = text.split('.');
  return integer.replace(/\B(?=(\d{3})+(?!\d))/g, ',') +
    (fraction === undefined ? '' : `.${fraction}`);
}
export function moneyUnits(value: string): bigint | null {
  const normalized = normalizeMoney(value);
  if (!/^\d+(\.\d{1,2})?$/.test(normalized)) return null;
  const [integer, fraction = ''] = normalized.split('.');
  return BigInt(integer) * 100n + BigInt(fraction.padEnd(2, '0'));
}
export function unitsMoney(value: bigint): string {
  return `${value / 100n}.${(value % 100n).toString().padStart(2, '0')}`;
}
export function chartNumber(value: string | null | undefined): number | null {
  if (value === null || value === undefined || !/^-?\d+(\.\d+)?$/.test(value)) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}
export function formatDecimal(value: string | null | undefined, digits = 2): string {
  if (value === null || value === undefined || !/^-?\d+(\.\d+)?$/.test(value)) return 'Sin dato';
  const [integer, fraction = ''] = value.split('.');
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return digits ? `${grouped},${fraction.padEnd(digits, '0').slice(0, digits)}` : grouped;
}
