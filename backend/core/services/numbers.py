from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal('0.01')
PERCENT = Decimal('0.0001')
RATE = Decimal('0.000000000001')
INDICATOR = Decimal('0.000001')
USD_PER_MILES_MILLONES = Decimal('1000000000')


def quantize(value, precision=CENT):
    return Decimal(value).quantize(precision, rounding=ROUND_HALF_UP)


def usd_miles_millones_a_usd(value):
    """Un USD_MILES_MILLONES equivale exactamente a 10**9 USD."""
    return quantize(value * USD_PER_MILES_MILLONES)


def valor_en_usd(indicator):
    if indicator.unidad == 'USD_MILES_MILLONES':
        return usd_miles_millones_a_usd(indicator.valor)
    if indicator.unidad == 'USD':
        return indicator.valor
    raise ValueError('El indicador no está expresado en USD.')


def moneda_local_a_usd(amount, exchange):
    if exchange.moneda_destino != 'USD':
        raise ValueError('Se requiere una tasa almacenada con destino USD.')
    return quantize(amount * exchange.tasa)
