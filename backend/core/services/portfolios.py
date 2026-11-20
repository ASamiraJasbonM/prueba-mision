from decimal import Decimal
from collections import defaultdict

from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.api import Conflict
from core.audit import audit
from core.models import Portafolio, Posicion, IndiceRiesgo
from .numbers import quantize


def check_writer(user, portfolio=None):
    if user.rol not in ["ADMIN", "ANALISTA"]:
        raise PermissionDenied("Tu rol no permite modificar portafolios.")
    if portfolio and user.rol != "ADMIN" and portfolio.usuario_id != user.pk:
        raise PermissionDenied("Solo el dueño o ADMIN puede modificar este portafolio.")


def lock_portfolio(user, pk, version):
    portfolio = get_object_or_404(Portafolio.objects.select_for_update(), pk=pk)
    check_writer(user, portfolio)
    if version is None:
        raise ValidationError({"version": "Envía la versión actual del portafolio."})
    if portfolio.version != version:
        raise Conflict()
    return portfolio


def touch(portfolio):
    portfolio.version += 1
    portfolio.fecha_modificacion = timezone.now()
    portfolio.save()


@transaction.atomic
def create_portfolio(user, data):
    check_writer(user)
    portfolio = Portafolio(usuario=user, **data)
    portfolio.full_clean()
    portfolio.save()
    audit(user, "CREAR", portfolio)
    return portfolio


@transaction.atomic
def update_portfolio(user, pk, version, data):
    portfolio = lock_portfolio(user, pk, version)
    for key, value in data.items():
        setattr(portfolio, key, value)
    portfolio.full_clean()
    touch(portfolio)
    audit(user, "EDITAR", portfolio, {"version": portfolio.version})
    return portfolio


@transaction.atomic
def delete_portfolio(user, pk, version):
    portfolio = lock_portfolio(user, pk, version)
    portfolio.activo = False
    touch(portfolio)
    audit(user, "ELIMINAR", portfolio)


def validate_position(position, exclude_pk=None):
    position.full_clean()
    if position.tipo_activo == "MONEDA" and position.pais.moneda_id == "USD":
        raise ValidationError(
            {"tipo_activo": "No se permite MONEDA para un país cuya moneda es USD."}
        )
    active = Posicion.objects.filter(
        portafolio=position.portafolio, fecha_salida__isnull=True
    )
    if exclude_pk:
        active = active.exclude(pk=exclude_pk)
    if active.filter(pais=position.pais, tipo_activo=position.tipo_activo).count() >= 2:
        raise ValidationError(
            {
                "tipo_activo": "Máximo dos posiciones activas del mismo tipo en el mismo país."
            }
        )
    total = (
        sum(active.values_list("monto_inversion_usd", flat=True), Decimal("0"))
        + position.monto_inversion_usd
    )
    if total > Decimal("50000000"):
        raise ValidationError(
            {"monto_inversion_usd": "El total activo no puede superar USD 50.000.000."}
        )


@transaction.atomic
def add_position(user, pk, version, data):
    portfolio = lock_portfolio(user, pk, version)
    position = Posicion(portafolio=portfolio, **data)
    validate_position(position)
    position.save()
    touch(portfolio)
    audit(
        user,
        "CREAR",
        position,
        {"portafolio_id": portfolio.pk, "version": portfolio.version},
    )
    return position


@transaction.atomic
def edit_position(user, pk, position_pk, version, data):
    portfolio = lock_portfolio(user, pk, version)
    position = get_object_or_404(Posicion.objects, pk=position_pk, portafolio=portfolio)
    if position.fecha_salida is not None:
        raise ValidationError(
            {
                "fecha_salida": "La posición está cerrada; no se permite editarla ni reabrirla."
            }
        )
    for key, value in data.items():
        setattr(position, key, value)
    validate_position(position, exclude_pk=position.pk)
    position.save()
    touch(portfolio)
    audit(user, "EDITAR", position, {"version": portfolio.version})
    return position


@transaction.atomic
def close_position(user, pk, position_pk, version):
    portfolio = lock_portfolio(user, pk, version)
    position = get_object_or_404(Posicion.objects, pk=position_pk, portafolio=portfolio)
    if position.fecha_salida is not None:
        raise Conflict("La posición ya está cerrada.")
    position.fecha_salida = timezone.now().date()
    position.full_clean()
    position.save(update_fields=["fecha_salida"])
    touch(portfolio)
    audit(user, "ELIMINAR", position, {"cierre": True, "version": portfolio.version})
    return position


@transaction.atomic
def delete_position(user, pk, position_pk, version):
    portfolio = lock_portfolio(user, pk, version)
    position = get_object_or_404(Posicion.objects, pk=position_pk, portafolio=portfolio)
    # Audit before deleting so the record retains its identity in the log.
    audit(
        user, "ELIMINAR", position, {"permanente": True, "version": portfolio.version}
    )
    position.delete()
    touch(portfolio)


def portfolio_summary(portfolio):
    by_country, by_type = (
        defaultdict(lambda: Decimal("0")),
        defaultdict(lambda: Decimal("0")),
    )
    total, covered, weighted = Decimal("0"), Decimal("0"), Decimal("0")
    missing = set()
    positions = list(portfolio.posiciones.filter(fecha_salida__isnull=True))
    country_ids = {position.pais_id for position in positions}
    latest = (
        IndiceRiesgo.objects.filter(pais_id=OuterRef("pais_id"))
        .order_by("-fecha_calculo", "-pk")
        .values("pk")[:1]
    )
    risks = (
        {
            risk.pais_id: risk
            for risk in IndiceRiesgo.objects.filter(
                pais_id__in=country_ids, pk=Subquery(latest)
            ).only("pais_id", "indice_compuesto", "detalle_calculo")
        }
        if country_ids
        else {}
    )
    for position in positions:
        amount = position.monto_inversion_usd
        total += amount
        by_country[position.pais_id] += amount
        by_type[position.tipo_activo] += amount
        risk = risks.get(position.pais_id)
        if risk:
            weighted += risk.indice_compuesto * amount
            covered += amount
            if risk.detalle_calculo.get("parcial"):
                missing.add(position.pais_id)
        else:
            missing.add(position.pais_id)

    def distribution(groups):
        return [
            {
                "codigo": key,
                "monto_usd": str(quantize(value)),
                "porcentaje": str(quantize(value / total * 100)) if total else "0.00",
            }
            for key, value in sorted(groups.items())
        ]

    return {
        "total_invertido_usd": str(quantize(total)),
        "posiciones_activas": len(positions),
        "por_pais": distribution(by_country),
        "por_tipo_activo": distribution(by_type),
        "riesgo_promedio_ponderado": str(quantize(weighted / covered))
        if covered
        else None,
        "monto_con_riesgo_usd": str(quantize(covered)),
        "paises_con_datos_faltantes": sorted(missing),
        "version": portfolio.version,
    }
