from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Moneda, Pais, Usuario, IndicadorEconomico, TipoCambio, Portafolio, Posicion
from core.services.numbers import quantize, RATE, PERCENT
from core.services.risk import recalculate
from core.services.sync import INDICATORS

# Geography/region/currency follow the PDF. Populations, indicators and rates are
# explicitly synthetic demonstration data, never represented as real API data.
COUNTRIES = [
    ('CO', 'Colombia', 'COP', 'Peso colombiano', 'ANDINA', '4.5709', '-74.2973', 52000000, '0.000250'),
    ('BR', 'Brasil', 'BRL', 'Real brasileño', 'CONO_SUR', '-14.2350', '-51.9253', 210000000, '0.200000'),
    ('MX', 'México', 'MXN', 'Peso mexicano', 'CENTROAMERICA', '23.6345', '-102.5528', 130000000, '0.050000'),
    ('AR', 'Argentina', 'ARS', 'Peso argentino', 'CONO_SUR', '-38.4161', '-63.6167', 46000000, '0.001000'),
    ('CL', 'Chile', 'CLP', 'Peso chileno', 'CONO_SUR', '-35.6751', '-71.5430', 20000000, '0.001100'),
    ('PE', 'Perú', 'PEN', 'Sol', 'ANDINA', '-9.1900', '-75.0152', 34000000, '0.270000'),
    ('EC', 'Ecuador', 'USD', 'Dólar estadounidense', 'ANDINA', '-1.8312', '-78.1834', 18000000, '1.000000'),
    ('UY', 'Uruguay', 'UYU', 'Peso uruguayo', 'CONO_SUR', '-32.5228', '-55.7658', 3500000, '0.025000'),
    ('PY', 'Paraguay', 'PYG', 'Guaraní', 'CONO_SUR', '-23.4425', '-58.4438', 7000000, '0.000130'),
    ('PA', 'Panamá', 'PAB', 'Balboa', 'CENTROAMERICA', '8.5380', '-80.7821', 4500000, '1.000000'),
]


class Command(BaseCommand):
    help = 'Seed DEMO sintético, offline e idempotente. No sobrescribe datos existentes.'

    @transaction.atomic
    def handle(self, *args, **options):
        today = timezone.now().date()
        users = {}
        for prefix, role in [('admin', 'ADMIN'), ('analista', 'ANALISTA'), ('viewer', 'VIEWER')]:
            email = f'{prefix}@datapulse.com'
            user = Usuario.objects.filter(email=email).first()
            if user is None:
                creator = Usuario.objects.create_superuser if role == 'ADMIN' else Usuario.objects.create_user
                user = creator(email, 'DataPulse2026!', nombre_completo=f'{prefix.title()} demo', rol=role)
            users[prefix] = user
        for index, (code, name, currency, currency_name, region, lat, lon, population, base_rate) in enumerate(COUNTRIES):
            money, _ = Moneda.objects.get_or_create(codigo=currency, defaults={'nombre': currency_name})
            country, _ = Pais.todos.get_or_create(codigo_iso=code, defaults={
                'nombre': name, 'moneda': money, 'region': region, 'latitud': Decimal(lat),
                'longitud': Decimal(lon), 'poblacion': population,
                'bandera_url': f'https://flags.restcountries.com/v5/svg/{code.lower()}.svg'})
            for year in range(today.year-5, today.year):
                values = {
                    'PIB': Decimal('100000000000') * (index+1) * (100 + (year-(today.year-5))*3) / 100,
                    'PIB_PERCAPITA': Decimal('4000') + index*1500,
                    'INFLACION': Decimal('60') if code == 'AR' else Decimal('3') + index,
                    'DESEMPLEO': Decimal('5') + index,
                    'BALANZA_COMERCIAL': Decimal('-5') + index,
                    'DEUDA_PIB': Decimal('30') + index*5,
                }
                for kind, value in values.items():
                    IndicadorEconomico.objects.get_or_create(pais=country, tipo=kind, anio=year,
                        defaults={'valor': value, 'unidad': INDICATORS[kind][1], 'fuente': 'MANUAL'})
            # 31 observations give 30 daily variations, meeting the 30-day minimum.
            for day in range(31):
                business_date = today-timedelta(days=30-day)
                previous = TipoCambio.objects.filter(moneda_origen=money, moneda_destino='USD',
                    fecha=business_date-timedelta(days=1)).first()
                rate = quantize(Decimal(base_rate) * (1 + Decimal(day)/1000), RATE) if currency not in ['USD', 'PAB'] else Decimal('1')
                change = quantize((rate / previous.tasa - 1)*100, PERCENT) if previous else None
                TipoCambio.objects.get_or_create(moneda_origen=money, moneda_destino='USD', fecha=business_date,
                    defaults={'tasa': rate, 'variacion_porcentual': change, 'fuente': 'DEMO_SINTETICO'})
        for index, name in enumerate(['Latam diversificado demo', 'Renta fija demo']):
            portfolio, _ = Portafolio.todos.get_or_create(usuario=users['analista'], nombre=name,
                defaults={'descripcion': 'Datos sintéticos de demostración; no representan inversiones reales.', 'es_publico': index == 0})
            for code in (['CO', 'BR', 'MX'] if index == 0 else ['CL', 'PE']):
                # Stable demo identity: changing the business date must not add an investment.
                if not Posicion.objects.filter(portafolio=portfolio, pais_id=code, tipo_activo='RENTA_FIJA').exists():
                    Posicion.objects.create(portafolio=portfolio, pais_id=code, tipo_activo='RENTA_FIJA',
                        fecha_entrada=today-timedelta(days=10), monto_inversion_usd=Decimal('10000.00'), notas='DEMO')
        report = recalculate()
        self.stdout.write(f'Seed DEMO listo: 10 países, 5 años, 31 fechas de cambio, 3 usuarios, 2 portafolios. IRPC nuevos: {report["calculados"]}.')
