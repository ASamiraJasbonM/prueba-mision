import hashlib
from django.db import transaction
from core.models import Alerta


@transaction.atomic
def emit(pais, tipo, severity, title, message, key):
    return Alerta.objects.get_or_create(clave_evento=key, defaults={
        'pais': pais, 'tipo_alerta': tipo, 'severidad': severity, 'titulo': title, 'mensaje': message})[0]


def indicator_alert(pais, changed_rows):
    if not changed_rows:
        return
    signature = hashlib.sha256('|'.join(sorted(changed_rows)).encode()).hexdigest()
    emit(pais, 'INDICADOR', 'INFO', 'Indicadores actualizados',
         'Se actualizaron los datos económicos del país.', f'indicadores:{pais.pk}:{signature}')


def exchange_alert(pais, exchange):
    if exchange.variacion_porcentual is not None and abs(exchange.variacion_porcentual) > 3:
        emit(pais, 'TIPO_CAMBIO', 'WARNING', 'Variación cambiaria significativa',
             f'La variación diaria fue {exchange.variacion_porcentual}%.',
             f'cambio:{pais.pk}:{exchange.fecha}:{exchange.tasa}:{exchange.variacion_porcentual}')
