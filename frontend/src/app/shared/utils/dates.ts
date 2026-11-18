export function utcToday(): string {
  return new Date().toISOString().slice(0, 10);
}
export function utcDaysAgo(days: number): string {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() - days);
  return date.toISOString().slice(0, 10);
}
