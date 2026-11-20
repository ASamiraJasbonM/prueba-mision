from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from core.models import IndiceRiesgo
from core.risk_api import RiesgoViewSet, RiesgoSerializer, RiesgoDetailSerializer
from .helpers import country


class RiskQueryBudgetTests(TestCase):
    def setUp(self):
        stamp = timezone.now()
        for code, currency in [('CO', 'COP'), ('BR', 'BRL'), ('CL', 'CLP')]:
            pais = country(code, currency)
            for score in ['80', '75', '80']:
                IndiceRiesgo.objects.create(pais=pais, fecha_calculo=stamp,
                    score_economico='80', score_cambiario='80', score_estabilidad='80',
                    indice_compuesto=Decimal(score), nivel_riesgo='BAJO')

    def test_ranking_serialization_uses_one_query_and_preserves_previous_value(self):
        view = RiesgoViewSet()
        view.action = 'list'
        with self.assertNumQueries(1):
            rows = RiesgoSerializer(view.get_queryset(), many=True).data
        self.assertEqual(len(rows), 3)
        self.assertEqual({row['variacion'] for row in rows}, {'5.00'})
        self.assertEqual({row['tendencia'] for row in rows}, {'SUBE'})

    def test_detail_history_uses_one_query_without_per_row_lookups(self):
        view = RiesgoViewSet()
        view.action = 'retrieve'
        latest = view.get_queryset().get(pais_id='CO')
        with self.assertNumQueries(1):
            data = RiesgoDetailSerializer(latest).data
        self.assertEqual([row['variacion'] for row in data['historico']], ['5.00', '-5.00', None])
        self.assertEqual([row['tendencia'] for row in data['historico']], ['SUBE', 'BAJA', 'SIN_HISTORICO'])
