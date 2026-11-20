"""Describe input provenance without changing scores or reclassifying legacy manual data."""
from datetime import date
from django.utils import timezone

KINDS = ['PIB', 'PIB_PERCAPITA', 'INFLACION', 'DESEMPLEO', 'DEUDA_PIB', 'BALANZA_COMERCIAL']


def risk_quality(risk):
    today = timezone.now().date()
    detail = risk.detalle_calculo or {}
    sources = detail.get('fuentes', {})
    counts = {'WORLD_BANK': 0, 'MANUAL': 0, 'DEMO_SINTETICO': 0, 'UNKNOWN': 0}
    delayed, undated = [], []
    for kind in KINDS:
        source = sources.get(kind, {})
        origin = source.get('fuente', 'UNKNOWN')
        counts[origin if origin in counts else 'UNKNOWN'] += 1
        year = source.get('anio')
        if not isinstance(year, int) or year > today.year or year < 1900:
            undated.append(kind)
        elif year < today.year-2:
            delayed.append(kind)
    rates = detail.get('tasas', [])
    dates = []
    for row in rates:
        try:
            dates.append(date.fromisoformat(row['fecha']))
        except (ValueError, KeyError, TypeError):
            continue
    rate_days = max(0, (today-max(dates)).days) if dates else None
    calculation_days = max(0, (today-risk.fecha_calculo.date()).days)
    external_rates = sum(row.get('fuente') == 'EXCHANGE_RATE_API' for row in rates)
    synthetic_rates = sum(row.get('fuente') == 'DEMO_SINTETICO' for row in rates)
    external_only = counts['WORLD_BANK'] == 6 and bool(rates) and external_rates == len(rates)
    invalid_rate_dates = len(dates) != len(rates) or any(value > today for value in dates)
    stale = bool(delayed or undated) or invalid_rate_dates or rate_days is None or rate_days > 2 or calculation_days > 1
    return {'indicadores_externos': counts['WORLD_BANK'], 'indicadores_manuales': counts['MANUAL'],
        'indicadores_sinteticos': counts['DEMO_SINTETICO'], 'indicadores_sin_origen': counts['UNKNOWN'],
        'tasas_externas': external_rates, 'tasas_sinteticas': synthetic_rates, 'tasas_total': len(rates),
        'indicadores_rezagados': sorted(delayed), 'indicadores_sin_fecha': sorted(undated), 'dias_desde_tasa': rate_days,
        'dias_desde_calculo': calculation_days, 'solo_fuentes_externas': external_only,
        'datos_rezagados': stale, 'requiere_revision': not external_only or stale or bool(detail.get('parcial', True))}
