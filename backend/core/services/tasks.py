import logging
from .sync import sync_indicators, sync_exchange, sync_countries
from .risk import recalculate

logger = logging.getLogger('datapulse')


def sync_and_recalculate(batch=False, progress=None):
    report = sync_indicators(batch=batch, progress=progress)
    # Even partial failures must leave updated countries with a fresh risk calculation.
    if progress:
        progress({'fase': 'RECALCULANDO'})
    report['riesgo'] = recalculate()
    return report


def exchange_and_recalculate():
    logger.info('sync_cambio_inicio')
    report = sync_exchange()
    report['riesgo'] = recalculate()
    logger.info('sync_cambio_fin', extra={'actualizados': report['actualizados'], 'errores': len(report['errores'])})
    return report
