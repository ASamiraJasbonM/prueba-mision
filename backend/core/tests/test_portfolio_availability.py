from core.models import Portafolio
from .helpers import APICase


class PortfolioAvailabilityTests(APICase):
    def setUp(self):
        super().setUp()
        self.target = Portafolio.objects.create(usuario=self.user, nombre='Editar')
        Portafolio.objects.create(usuario=self.user, nombre='Reservado por dueño')
        Portafolio.objects.create(usuario=self.admin, nombre='Reservado por admin')

    def available(self, name, target=None):
        query = {'nombre': name}
        if target is not None:
            query['excluir_id'] = target
        return self.client.get('/api/portafolios/nombre-disponible/', query)

    def test_admin_checks_the_target_owner_and_excludes_only_the_target(self):
        self.authenticate(self.admin)
        self.assertFalse(self.available('Reservado por dueño', self.target.pk).data['disponible'])
        self.assertTrue(self.available('Reservado por admin', self.target.pk).data['disponible'])
        self.assertTrue(self.available('Editar', self.target.pk).data['disponible'])
        self.assertFalse(self.available('Reservado por admin').data['disponible'])

    def test_foreign_portfolio_cannot_be_used_to_probe_a_different_owner(self):
        self.authenticate(self.viewer)
        self.assertEqual(self.available('Reservado por dueño', self.target.pk).status_code, 404)
        self.target.es_publico = True
        self.target.save()
        self.assertEqual(self.available('Reservado por dueño', self.target.pk).status_code, 403)
        self.authenticate(self.user)
        self.assertFalse(self.available('Reservado por dueño', self.target.pk).data['disponible'])
