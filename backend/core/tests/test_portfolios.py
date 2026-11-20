from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from core.models import Portafolio, Posicion, IndiceRiesgo
from .helpers import APICase, country


class PortfolioTests(APICase):
    def setUp(self):
        super().setUp()
        self.pais = country()
        self.usd = country("EC", "USD")
        self.authenticate()

    def create_portfolio(self, name="Portafolio demo"):
        response = self.client.post(
            "/api/portafolios/", {"nombre": name, "descripcion": "", "es_publico": True}
        )
        self.assertEqual(response.status_code, 201)
        return response.data

    def position(self, version, **extra):
        return {
            "pais": "CO",
            "tipo_activo": "RENTA_FIJA",
            "monto_inversion_usd": "1000.00",
            "fecha_entrada": str(timezone.now().date() - timedelta(days=1)),
            "version": version,
            **extra,
        }

    def test_end_to_end_with_conflict_and_pdf(self):
        portfolio = self.create_portfolio()
        url = f"/api/portafolios/{portfolio['id']}/"
        result = self.client.post(url + "posiciones/", self.position(1))
        self.assertEqual(result.status_code, 201)
        self.assertEqual(
            self.client.post(url + "posiciones/", self.position(1)).status_code, 409
        )
        summary = self.client.get(url + "resumen/")
        self.assertEqual(summary.data["total_invertido_usd"], "1000.00")
        pdf = self.client.get(url + "export/pdf/")
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF-"))
        response = self.client.delete(
            url + f"posiciones/{result.data['id']}/", HTTP_IF_MATCH='"2"'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.get(url + "resumen/").data["total_invertido_usd"], "0.00"
        )
        self.assertEqual(Posicion.objects.count(), 1)
        self.assertEqual(self.client.delete(url, HTTP_IF_MATCH='"3"').status_code, 204)
        self.assertFalse(Portafolio.objects.exists())
        self.assertEqual(Portafolio.todos.count(), 1)

    def test_roles_and_public_is_read_only_for_other_analyst(self):
        portfolio = self.create_portfolio()
        self.authenticate(self.viewer)
        self.assertEqual(self.client.get("/api/portafolios/").data["count"], 1)
        self.assertEqual(
            self.client.post(
                "/api/portafolios/", {"nombre": "No permitido"}
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                f"/api/portafolios/{portfolio['id']}/posiciones/", self.position(1)
            ).status_code,
            403,
        )
        self.authenticate(self.admin)
        response = self.client.put(
            f"/api/portafolios/{portfolio['id']}/",
            {
                "nombre": "Editado por admin",
                "descripcion": "",
                "es_publico": True,
                "version": 1,
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_cross_rules_and_edit_does_not_count_itself(self):
        portfolio = self.create_portfolio()
        url = f"/api/portafolios/{portfolio['id']}/posiciones/"
        self.assertEqual(
            self.client.post(
                url, self.position(1, pais="EC", tipo_activo="MONEDA")
            ).status_code,
            400,
        )
        first = self.client.post(url, self.position(1))
        self.assertEqual(first.status_code, 201)
        self.assertEqual(self.client.post(url, self.position(2)).status_code, 201)
        self.assertEqual(self.client.post(url, self.position(3)).status_code, 400)
        edit = self.client.put(
            url + f"{first.data['id']}/",
            self.position(3, monto_inversion_usd="2000.00"),
        )
        self.assertEqual(edit.status_code, 200)
        self.assertEqual(edit.data["monto_inversion_usd"], "2000.00")

    def test_dates_amounts_and_portfolio_limit(self):
        portfolio = self.create_portfolio()
        url = f"/api/portafolios/{portfolio['id']}/posiciones/"
        self.assertEqual(
            self.client.post(
                url, self.position(1, monto_inversion_usd="999.99")
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                url,
                self.position(
                    1, fecha_entrada=str(timezone.now().date() + timedelta(days=1))
                ),
            ).status_code,
            400,
        )
        for i in range(5):
            Posicion.objects.create(
                portafolio_id=portfolio["id"],
                pais=self.pais,
                tipo_activo="COMMODITIES",
                monto_inversion_usd="10000000",
                fecha_entrada=timezone.now().date() - timedelta(days=1),
            )
        self.assertEqual(self.client.post(url, self.position(1)).status_code, 400)

    def test_unique_name_check_includes_deleted(self):
        portfolio = self.create_portfolio()
        response = self.client.get(
            "/api/portafolios/nombre-disponible/?nombre=Portafolio%20demo"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["disponible"])
        self.assertEqual(
            self.client.post(
                "/api/portafolios/", {"nombre": "Portafolio demo"}
            ).status_code,
            400,
        )

    def test_same_day_close_rejected_and_private_hidden(self):
        portfolio = self.create_portfolio()
        url = f"/api/portafolios/{portfolio['id']}/"
        position = self.client.post(
            url + "posiciones/",
            self.position(1, fecha_entrada=str(timezone.now().date())),
        )
        self.assertEqual(position.status_code, 201)
        self.assertEqual(
            self.client.delete(
                url + f"posiciones/{position.data['id']}/", HTTP_IF_MATCH='"2"'
            ).status_code,
            400,
        )
        self.assertIsNone(Posicion.objects.get(pk=position.data["id"]).fecha_salida)
        Portafolio.objects.filter(pk=portfolio["id"]).update(es_publico=False)
        self.authenticate(self.viewer)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_position_hard_delete_removes_row_and_touches_version(self):
        portfolio = self.create_portfolio()
        url = f"/api/portafolios/{portfolio['id']}/"
        position = self.client.post(url + "posiciones/", self.position(1))
        self.assertEqual(position.status_code, 201)
        self.assertEqual(Posicion.objects.count(), 1)
        response = self.client.delete(
            url + f"posiciones/{position.data['id']}/eliminar/?motivo=ERROR_CREACION", HTTP_IF_MATCH='"2"'
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Posicion.objects.count(), 0)
        self.assertEqual(self.client.get(url).data["version"], 3)
        self.assertEqual(self.client.get(url).data["posiciones"], [])

    def test_position_hard_delete_requires_current_version(self):
        portfolio = self.create_portfolio()
        url = f"/api/portafolios/{portfolio['id']}/"
        position = self.client.post(url + "posiciones/", self.position(1))
        self.assertEqual(position.status_code, 201)
        response = self.client.delete(
            url + f"posiciones/{position.data['id']}/eliminar/?motivo=ERROR_CREACION", HTTP_IF_MATCH='"1"'
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Posicion.objects.count(), 1)
