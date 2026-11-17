from decimal import Decimal
from datetime import date

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from core.models import Usuario


class ModelTests(TestCase):
    def test_currency_can_be_shared(self):
        Moneda = apps.get_model('core', 'Moneda')
        Pais = apps.get_model('core', 'Pais')
        currency = Moneda.objects.create(codigo='USD', nombre='Dólar')
        for code in ['EC', 'XX']:
            Pais.objects.create(codigo_iso=code, nombre=code, moneda=currency, region='ANDINA',
                                latitud='0', longitud='0', poblacion=1)
        self.assertEqual(Pais.objects.filter(moneda=currency).count(), 2)

    def test_unique_portfolio_name_including_deleted(self):
        Portafolio = apps.get_model('core', 'Portafolio')
        user = Usuario.objects.create_user('owner@example.com')
        Portafolio.objects.create(nombre='Demo', usuario=user, activo=False)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Portafolio.objects.create(nombre='Demo', usuario=user)
        self.assertEqual(Portafolio.objects.count(), 0)
        self.assertEqual(Portafolio.todos.count(), 1)

    def test_indicator_and_exchange_natural_keys(self):
        from core.models import Moneda, Pais, IndicadorEconomico, TipoCambio
        moneda = Moneda.objects.create(codigo='COP', nombre='Peso')
        pais = Pais.objects.create(codigo_iso='CO', nombre='Colombia', moneda=moneda,
                                   region='ANDINA', latitud=0, longitud=0, poblacion=1)
        data = dict(pais=pais, tipo='PIB', anio=2025, valor=Decimal('100'), unidad='USD')
        IndicadorEconomico.objects.create(**data)
        with self.assertRaises(IntegrityError), transaction.atomic():
            IndicadorEconomico.objects.create(**data)
        data = dict(moneda_origen=moneda, fecha=date(2026, 1, 1), tasa=Decimal('0.000250'))
        TipoCambio.objects.create(**data)
        with self.assertRaises(IntegrityError), transaction.atomic():
            TipoCambio.objects.create(**data)

    def test_date_and_score_constraints_at_database_and_model(self):
        from core.models import Moneda, Pais, Portafolio, Posicion, IndiceRiesgo
        moneda = Moneda.objects.create(codigo='COP', nombre='Peso')
        pais = Pais.objects.create(codigo_iso='CO', nombre='Colombia', moneda=moneda,
                                   region='ANDINA', latitud=0, longitud=0, poblacion=1)
        user = Usuario.objects.create_user('owner@example.com')
        portfolio = Portafolio.objects.create(nombre='Demo', usuario=user)
        position = Posicion(portafolio=portfolio, pais=pais, tipo_activo='RENTA_FIJA',
                            monto_inversion_usd='1000', fecha_entrada=date(2025, 1, 1),
                            fecha_salida=date(2025, 1, 1))
        with self.assertRaises(ValidationError):
            position.clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            position.save()
        risk = IndiceRiesgo(pais=pais, score_economico=0, score_cambiario=0,
                            score_estabilidad=0, indice_compuesto=101, nivel_riesgo='BAJO')
        with self.assertRaises(ValidationError):
            risk.clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            risk.save()
