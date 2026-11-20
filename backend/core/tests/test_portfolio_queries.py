from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from core.models import Usuario, Portafolio, Posicion, IndiceRiesgo
from core.services.portfolios import portfolio_summary
from .helpers import country


class PortfolioQueryTests(TestCase):
    def setUp(self):
        self.portfolio = Portafolio.objects.create(usuario=Usuario.objects.create_user('queries@test.com'), nombre='Consultas')

    def risk(self, pais, score, partial=False, stamp=None):
        return IndiceRiesgo.objects.create(pais=pais, fecha_calculo=stamp or timezone.now(),
            score_economico=score, score_cambiario=score, score_estabilidad=score,
            indice_compuesto=score, nivel_riesgo='BAJO', detalle_calculo={'parcial': partial})

    def test_summary_has_constant_query_budget_and_preserves_coverage_and_latest_ties(self):
        co, br, mx, cl = [country(code, currency) for code, currency in [('CO','COP'), ('BR','BRL'), ('MX','MXN'), ('CL','CLP')]]
        stamp = timezone.now()
        self.risk(co, '20', stamp=stamp)
        self.risk(co, '80', stamp=stamp)
        self.risk(co, '10', stamp=stamp-timedelta(days=1))
        self.risk(br, '0', partial=True)
        for pais, amount, asset, closed in [(co, '1000', 'RENTA_FIJA', False), (co, '1000', 'RENTA_VARIABLE', False),
                (br, '2000', 'RENTA_FIJA', False), (mx, '1000', 'RENTA_FIJA', False), (cl, '9000', 'RENTA_FIJA', True)]:
            Posicion.objects.create(portafolio=self.portfolio, pais=pais, tipo_activo=asset, monto_inversion_usd=amount,
                fecha_entrada=stamp.date()-timedelta(days=2), fecha_salida=stamp.date()-timedelta(days=1) if closed else None)
        with self.assertNumQueries(2):
            result = portfolio_summary(self.portfolio)
        self.assertEqual(result['total_invertido_usd'], '5000.00')
        self.assertEqual(result['monto_con_riesgo_usd'], '4000.00')
        self.assertEqual(result['riesgo_promedio_ponderado'], '40.00')
        self.assertEqual(result['paises_con_datos_faltantes'], ['BR', 'MX'])
        self.assertEqual(result['posiciones_activas'], 4)
        self.assertEqual(result['por_pais'], [
            {'codigo':'BR','monto_usd':'2000.00','porcentaje':'40.00'},
            {'codigo':'CO','monto_usd':'2000.00','porcentaje':'40.00'},
            {'codigo':'MX','monto_usd':'1000.00','porcentaje':'20.00'}])

    def test_empty_portfolio_does_not_query_risk_history(self):
        with self.assertNumQueries(1):
            result = portfolio_summary(self.portfolio)
        self.assertEqual(result['total_invertido_usd'], '0.00')
        self.assertIsNone(result['riesgo_promedio_ponderado'])
