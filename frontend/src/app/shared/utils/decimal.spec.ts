import { chartNumber, formatDecimal, moneyUnits, normalizeMoney } from './decimal';

describe('Decimales de API y dinero exacto', () => {
  it('conserva centavos sin usar coma flotante para decisiones', () => {
    expect(moneyUnits('10000000.01')).toBe(1000000001n);
    expect(moneyUnits('1,234.56')).toBe(123456n);
    expect(moneyUnits('1000.001')).toBeNull();
    expect(moneyUnits('NaN')).toBeNull();
    expect(normalizeMoney('1,234.50')).toBe('1234.50');
  });
  it('distingue ausencia, cero y parseos inválidos para gráficos', () => {
    expect(chartNumber(null)).toBeNull();
    expect(chartNumber('0.000000')).toBe(0);
    expect(chartNumber('Infinity')).toBeNull();
    expect(chartNumber('12error')).toBeNull();
  });
  it('muestra valores grandes sin perder precisión', () => {
    expect(formatDecimal('1234567890123456789012.123456', 6)).toBe(
      '1.234.567.890.123.456.789.012,123456',
    );
    expect(formatDecimal(null)).toBe('Sin dato');
  });
});
