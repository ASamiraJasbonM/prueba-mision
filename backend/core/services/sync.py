import logging
from datetime import datetime, timezone as dt_timezone, timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction, DatabaseError
from django.utils import timezone
import requests

from core.models import Pais, Moneda, IndicadorEconomico, TipoCambio
from .http import get_json
from .numbers import quantize, RATE, PERCENT, INDICATOR
from .alerts import indicator_alert, exchange_alert
from core.audit import audit

logger = logging.getLogger('datapulse')
INDICATORS = {
    'PIB': ('NY.GDP.MKTP.CD', 'USD'),
    'INFLACION': ('FP.CPI.TOTL.ZG', 'PORCENTAJE'),
    'DESEMPLEO': ('SL.UEM.TOTL.ZS', 'PORCENTAJE'),
    'BALANZA_COMERCIAL': ('NE.RSB.GNFS.ZS', 'PORCENTAJE'),
    'DEUDA_PIB': ('GC.DOD.TOTL.GD.ZS', 'PORCENTAJE'),
    'PIB_PERCAPITA': ('NY.GDP.PCAP.CD', 'USD'),
}
SYNC_ERRORS = (requests.RequestException, ValueError, KeyError, TypeError, IndexError,
               InvalidOperation, ValidationError, DatabaseError)


def report_error(report, country, operation, exc):
    error = {'pais': country, 'operacion': operation, 'code': type(exc).__name__, 'mensaje': 'No se pudieron actualizar los datos; se conservan los anteriores.'}
    report['errores'].append(error)
    logger.error('sync_error', extra={'pais': country, 'operacion': operation, 'error_code': type(exc).__name__})


@transaction.atomic
def persist_indicator(pais, tipo, year, value, unit):
    # Serialize writes by country; no network calls inside this transaction.
    Pais.objects.select_for_update().get(pk=pais.pk)
    defaults = {'valor': quantize(Decimal(str(value)), INDICATOR), 'unidad': unit, 'fuente': 'WORLD_BANK'}
    candidate = IndicadorEconomico(pais=pais, tipo=tipo, anio=year, **defaults)
    candidate.full_clean(validate_unique=False, validate_constraints=False)
    current = IndicadorEconomico.objects.filter(pais=pais, tipo=tipo, anio=year).first()
    if current and all(getattr(current, key) == val for key, val in defaults.items()):
        return False
    obj, created = IndicadorEconomico.objects.update_or_create(pais=pais, tipo=tipo, anio=year,
        defaults={**defaults, 'fecha_actualizacion': timezone.now()})
    audit(None, 'CREAR' if created else 'EDITAR', obj)
    return True


def _fetch_indicator_group(group, by_code, tipo, code, unit, year, report, changed_rows, batch, progress=None):
    # Fetch one indicator for a group of countries and persist the rows. In
    # batch mode a request-level failure returns False without logging errors
    # so the caller can retry each country individually; single-country calls
    # log their own error and return False.
    try:
        page = 1
        while True:
            codes = ';'.join(by_code)
            if progress:
                progress({'fase': 'INDICADORES', 'indicador': tipo, 'paises': list(by_code),
                    'actualizados': report['actualizados']})
            payload = get_json(f'{settings.WORLD_BANK_URL}/country/{codes}/indicator/{code}',
                params={'date': f'{year-4}:{year}', 'format': 'json', 'per_page': 100, 'page': page})
            if progress:
                progress({'fase': 'GUARDANDO', 'indicador': tipo, 'paises': list(by_code),
                    'actualizados': report['actualizados']})
            if not isinstance(payload, list) or len(payload) != 2 or not isinstance(payload[0], dict):
                raise ValueError('Respuesta inválida de World Bank.')
            for row in payload[1] or []:
                # A batched result must identify its country explicitly; never
                # assign an ambiguous or foreign row to a user country.
                row_code = row.get('country', {}).get('id') if batch else group[0].pk
                pais = by_code.get(row_code)
                if pais is None or row.get('value') is None:
                    continue
                try:
                    row_year = int(row['date'])
                    if year-4 <= row_year <= year:
                        changed = persist_indicator(pais, tipo, row_year, row['value'], unit)
                        report['actualizados'] += int(changed)
                        if changed:
                            changed_rows[pais.pk].append(f'{tipo}:{row_year}:{row["value"]}')
                except SYNC_ERRORS as exc:
                    report_error(report, pais.pk, tipo, exc)
            if page >= min(int(payload[0].get('pages', 1)), 10):
                break
            page += 1
        report['consultas_exitosas'] += 1
        return True
    except SYNC_ERRORS as exc:
        if not batch:
            for pais in group:
                report_error(report, pais.pk, tipo, exc)
        return False


def sync_indicators(batch=False, progress=None):
    report = {'paises_procesados': 0, 'actualizados': 0, 'errores': [], 'paises': [], 'consultas_exitosas': 0}
    year = timezone.now().year - 1
    logger.info('sync_indicadores_inicio')
    countries = list(Pais.objects.all())
    # The official API accepts semicolon-separated ISO-2 codes. Scheduled work
    # uses six requests for ten countries instead of sixty, and falls back to
    # one request per country when a batched request is rejected by the API.
    groups = [countries] if batch and countries else [[country] for country in countries]
    for group in groups:
        by_code = {country.pk: country for country in group}
        changed_rows = {country.pk: [] for country in group}
        for tipo, (code, unit) in INDICATORS.items():
            ok = _fetch_indicator_group(group, by_code, tipo, code, unit, year, report, changed_rows, batch, progress)
            if not ok and batch:
                for country in group:
                    _fetch_indicator_group([country], {country.pk: country}, tipo, code, unit, year, report, changed_rows, False, progress)
        for pais in group:
            report['paises_procesados'] += 1
            report['paises'].append(pais.pk)
            indicator_alert(pais, changed_rows[pais.pk])
    logger.info('sync_indicadores_fin', extra={'actualizados': report['actualizados'], 'errores': len(report['errores']), 'paises_procesados': report['paises_procesados'], 'paises': report['paises']})
    return report


@transaction.atomic
def persist_exchange(currency, business_date, units_per_usd):
    Moneda.objects.select_for_update().get(pk=currency.pk)
    if units_per_usd <= 0 or not units_per_usd.is_finite():
        raise ValueError('Tasa no positiva.')
    rate = quantize(Decimal('1') / units_per_usd, RATE)
    previous = TipoCambio.objects.filter(moneda_origen=currency, moneda_destino='USD', fecha=business_date-timedelta(days=1)).first()
    change = quantize((rate / previous.tasa - 1) * 100, PERCENT) if previous else None
    candidate = TipoCambio(moneda_origen=currency, fecha=business_date, tasa=rate, variacion_porcentual=change)
    candidate.full_clean(validate_unique=False, validate_constraints=False)
    current = TipoCambio.objects.filter(moneda_origen=currency, moneda_destino='USD', fecha=business_date).first()
    if current and current.tasa == rate and current.variacion_porcentual == change and current.fuente == 'EXCHANGE_RATE_API':
        return False
    obj, created = TipoCambio.objects.update_or_create(moneda_origen=currency, moneda_destino='USD', fecha=business_date,
        defaults={'tasa': rate, 'variacion_porcentual': change, 'fuente': 'EXCHANGE_RATE_API'})
    audit(None, 'CREAR' if created else 'EDITAR', obj)
    following = TipoCambio.objects.filter(moneda_origen=currency, moneda_destino='USD', fecha=business_date+timedelta(days=1)).first()
    if following:
        following.variacion_porcentual = quantize((following.tasa / rate - 1) * 100, PERCENT)
        following.save(update_fields=['variacion_porcentual'])
    return True


def sync_exchange(business_date=None):
    report = {'actualizados': 0, 'errores': []}
    try:
        payload = get_json(settings.EXCHANGE_RATE_URL)
        if payload.get('result', 'success') != 'success' or payload.get('base_code', payload.get('base')) != 'USD':
            raise ValueError('Se requiere base USD.')
        rates = payload['rates']
        if business_date is None:
            timestamp = payload.get('time_last_update_unix', payload.get('time_last_updated'))
            if timestamp is None:
                raise ValueError('Falta fecha de proveedor.')
            business_date = datetime.fromtimestamp(int(timestamp), tz=dt_timezone.utc).date()
        for currency in Moneda.objects.filter(paises__activo=True).distinct():
            try:
                raw = Decimal('1') if currency.pk == 'USD' else Decimal(str(rates[currency.pk]))
                report['actualizados'] += int(persist_exchange(currency, business_date, raw))
                exchange = TipoCambio.objects.get(moneda_origen=currency, moneda_destino='USD', fecha=business_date)
                for pais in Pais.objects.filter(moneda=currency):
                    exchange_alert(pais, exchange)
            except SYNC_ERRORS as exc:
                report_error(report, currency.pk, 'TIPO_CAMBIO', exc)
    except SYNC_ERRORS as exc:
        report_error(report, '*', 'TIPO_CAMBIO', exc)
    return report


def sync_countries():
    report = {'actualizados': 0, 'errores': []}
    for country in Pais.objects.select_related('moneda'):
        try:
            if not settings.REST_COUNTRIES_API_KEY:
                raise ValueError('Falta REST_COUNTRIES_API_KEY.')
            payload = get_json(f'{settings.REST_COUNTRIES_URL}/codes.alpha_2/{country.pk}',
                headers={'Authorization': f'Bearer {settings.REST_COUNTRIES_API_KEY}'})
            row = payload['data']['objects'][0]
            if row['codes']['alpha_2'] != country.pk:
                raise ValueError('Código no coincide.')
            with transaction.atomic():
                locked = Pais.objects.select_for_update().get(pk=country.pk)
                locked.nombre = row['names']['official']
                locked.poblacion = int(row['population'])
                locked.bandera_url = row['flag']['url_svg']
                # Keep business regions/currency selection from the PDF (Panama PAB).
                for currency in row['currencies']:
                    if currency['code'] == locked.moneda_id:
                        Moneda.objects.filter(pk=locked.moneda_id).update(nombre=currency['name'])
                coordinates = row.get('coordinates', {})
                if isinstance(coordinates, dict) and 'lat' in coordinates and 'lng' in coordinates:
                    locked.latitud = quantize(Decimal(str(coordinates['lat'])), INDICATOR)
                    locked.longitud = quantize(Decimal(str(coordinates['lng'])), INDICATOR)
                locked.full_clean()
                locked.save()
                audit(None, 'EDITAR', locked)
            report['actualizados'] += 1
        except SYNC_ERRORS as exc:
            report_error(report, country.pk, 'PAIS', exc)
    return report
