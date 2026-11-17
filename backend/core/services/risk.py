import hashlib
import json
from datetime import timedelta
from decimal import Decimal, localcontext

from django.db import transaction
from django.utils import timezone
from core.models import Pais, IndiceRiesgo, IndicadorEconomico, TipoCambio
from .numbers import quantize, valor_en_usd
from .alerts import emit
from core.audit import audit


def penalty(value, thresholds, low=False):
    if value is None:
        return Decimal('0')
    for threshold, deduction in thresholds:
        if (value < threshold) if low else (value > threshold):
            return Decimal(deduction)
    return Decimal('0')


def economic_penalties(data):
    return {
        'PIB_PERCAPITA': penalty(data.get('PIB_PERCAPITA'), [(3000, 30), (6000, 15), (12000, 5)], low=True),
        'INFLACION': penalty(data.get('INFLACION'), [(50, 40), (10, 25), (5, 10)]),
        'DESEMPLEO': penalty(data.get('DESEMPLEO'), [(15, 25), (10, 15), (7, 5)]),
        'DEUDA_PIB': penalty(data.get('DEUDA_PIB'), [(80, 20), (50, 10)]),
    }


def score_economico(data):
    return max(Decimal('0'), Decimal('100') - sum(economic_penalties(data).values()))


def standard_deviation(values):
    if len(values) < 2:
        return None
    with localcontext() as context:
        context.prec = 38
        mean = sum(values) / Decimal(len(values))
        return (sum((value-mean)**2 for value in values) / Decimal(len(values))).sqrt()


def score_cambiario(variations, depreciation):
    volatility = standard_deviation(variations)
    deduction = penalty(volatility, [(Decimal('3'), 40), (Decimal('1.5'), 25), (Decimal('0.5'), 10)])
    deduction += penalty(depreciation, [(10, 30), (5, 15), (2, 5)])
    return max(Decimal('0'), Decimal('100') - deduction)


def stability_penalties(data):
    return {
        'BALANZA_COMERCIAL': penalty(data.get('BALANZA_COMERCIAL'), [(-10, 25), (-5, 15), (0, 5)], low=True),
        'CRECIMIENTO_PIB': penalty(data.get('CRECIMIENTO_PIB'), [(-2, 30), (0, 20), (1, 10)], low=True),
    }


def score_estabilidad(data):
    deductions = stability_penalties(data)
    negative_count = sum(value > 0 for value in {**economic_penalties(data), **deductions}.values())
    return max(Decimal('0'), Decimal('100') - sum(deductions.values()) - negative_count * 5)


def classify(value):
    value = quantize(value)
    for minimum, level in [(75, 'BAJO'), (50, 'MODERADO'), (25, 'ALTO')]:
        if value >= minimum:
            return level
    return 'CRITICO'


def calculate_scores(data, variations, depreciation):
    economic = score_economico(data)
    exchange = score_cambiario(variations, depreciation)
    stability = score_estabilidad(data)
    composite = quantize(economic * Decimal('.40') + exchange * Decimal('.30') + stability * Decimal('.30'))
    return {'score_economico': quantize(economic), 'score_cambiario': quantize(exchange),
            'score_estabilidad': quantize(stability), 'indice_compuesto': composite,
            'nivel_riesgo': classify(composite)}


@transaction.atomic
def calculate_country(country):
    country = Pais.objects.select_for_update().get(pk=country.pk)
    latest = {}
    for row in country.indicadores.order_by('tipo', '-anio'):
        latest.setdefault(row.tipo, row)
    data = {}
    sources = {}
    for tipo, row in latest.items():
        data[tipo] = valor_en_usd(row) if tipo in ['PIB', 'PIB_PERCAPITA'] else row.valor
        sources[tipo] = {'anio': row.anio, 'fuente': row.fuente, 'unidad': row.unidad,
                         'valor': str(row.valor), 'fecha': row.fecha_actualizacion.isoformat()}
    if 'PIB' in latest:
        current = latest['PIB']
        previous = country.indicadores.filter(tipo='PIB', anio=current.anio-1).first()
        if previous and previous.valor > 0:
            data['CRECIMIENTO_PIB'] = (data['PIB'] / valor_en_usd(previous) - 1) * 100
            sources['PIB_ANTERIOR'] = {'anio': previous.anio, 'valor_usd': str(valor_en_usd(previous)),
                                     'fecha': previous.fecha_actualizacion.isoformat(), 'fuente': previous.fuente}
    today = timezone.now().date()
    rates = list(TipoCambio.objects.filter(moneda_origen=country.moneda, moneda_destino='USD',
        fecha__gte=today-timedelta(days=30), fecha__lte=today).order_by('fecha'))
    variations = [row.variacion_porcentual for row in rates if row.variacion_porcentual is not None][-30:]
    depreciation = (rates[0].tasa / rates[-1].tasa - 1) * 100 if len(rates) >= 2 else None
    required = ['PIB', 'PIB_PERCAPITA', 'INFLACION', 'DESEMPLEO', 'DEUDA_PIB', 'BALANZA_COMERCIAL', 'CRECIMIENTO_PIB']
    missing = [key for key in required if key not in data]
    if len(variations) < 30:
        missing.append('VARIACIONES_30_DIAS')
    if not rates or rates[0].fecha != today-timedelta(days=30) or rates[-1].fecha != today:
        missing.append('DEPRECIACION_30_DIAS')
    detail = {'parcial': bool(missing), 'faltantes': missing, 'fuentes': sources,
        'fecha_negocio_utc': str(today), 'datos': {key: str(val) for key, val in data.items()},
        'tasas': [{'fecha': str(row.fecha), 'tasa': str(row.tasa), 'variacion': str(row.variacion_porcentual) if row.variacion_porcentual is not None else None,
                   'fuente': row.fuente} for row in rates],
        'volatilidad': str(standard_deviation(variations)) if len(variations) >= 2 else None,
        'depreciacion': str(depreciation) if depreciation is not None else None,
        'penalizaciones': {key: str(value) for key, value in {**economic_penalties(data), **stability_penalties(data)}.items()}}
    previous = country.riesgos.first()
    fingerprint = hashlib.sha256((country.pk + json.dumps(detail, sort_keys=True)).encode()).hexdigest()
    if previous and previous.detalle_calculo.get('firma_entradas') == fingerprint:
        return previous, False
    # A -> B -> A is a new event; only identical consecutive inputs are a retry.
    signature = hashlib.sha256((fingerprint + ':' + str(previous.pk if previous else 0)).encode()).hexdigest()
    detail['firma_entradas'] = fingerprint
    scores = calculate_scores(data, variations, depreciation)
    result = IndiceRiesgo.objects.create(pais=country, clave_calculo=signature, detalle_calculo=detail, **scores)
    audit(None, 'CREAR', result)
    if result.indice_compuesto < 25 and (not previous or previous.indice_compuesto >= 25):
        emit(country, 'RIESGO', 'CRITICAL', 'Riesgo crítico', 'El IRPC cayó por debajo de 25.', f'riesgo_critico:{signature}')
    if previous and previous.indice_compuesto - result.indice_compuesto > 15:
        emit(country, 'RIESGO', 'WARNING', 'Caída significativa del IRPC', 'El IRPC cayó más de 15 puntos.', f'riesgo_caida:{signature}')
    inflation = latest.get('INFLACION')
    if inflation and inflation.valor > 50:
        emit(country, 'INDICADOR', 'CRITICAL', 'Inflación superior al 50%',
             f'La inflación publicada es {inflation.valor}%.', f'inflacion:{country.pk}:{inflation.anio}:{inflation.valor}')
    return result, True


def recalculate():
    report = {'calculados': 0, 'existentes': 0, 'errores': []}
    for country in Pais.objects.all():
        try:
            _, created = calculate_country(country)
            report['calculados' if created else 'existentes'] += 1
        except (ValueError, ArithmeticError) as exc:
            import logging
            logging.getLogger('datapulse').error('riesgo_error', extra={'pais': country.pk, 'error_code': type(exc).__name__})
            report['errores'].append({'pais': country.pk, 'code': type(exc).__name__})
    return report
