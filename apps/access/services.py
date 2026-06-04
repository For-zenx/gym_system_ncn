import datetime

from apps.billing.cycle import (
    days_until_next_cut_date,
    is_subscription_suspended,
    next_cut_date,
    unpaid_fixed_periods,
)
from .models import AccessLog


def check_access_integrity(client):
    from django.utils import timezone

    active_memberships = client.active_memberships

    if not active_memberships.exists():
        if is_subscription_suspended(client):
            motivo = f"Suscripción suspendida (corte: día {client.fecha_corte_dia})"
        elif client.memberships.exists():
            latest = client.memberships.order_by('-fecha_fin').first()
            motivo = f"Membresía vencida el {latest.fecha_fin.strftime('%d/%m/%Y')}"
        else:
            motivo = "Sin membresía registrada"

        AccessLog.objects.create(
            client=client,
            resultado=False,
            motivo=motivo,
        )
        return False, motivo

    current_time = timezone.localtime().time()

    for membership in active_memberships:
        if membership.is_valid_now(current_time):
            AccessLog.objects.create(
                client=client,
                resultado=True,
                motivo="Acceso concedido",
            )
            return True, "Acceso concedido"

    AccessLog.objects.create(
        client=client,
        resultado=False,
        motivo="Fuera de horario permitido",
    )
    return False, "Fuera de horario permitido"


def _suspended_since_display(client, today=None):
    if today is None:
        today = datetime.date.today()
    unpaid = unpaid_fixed_periods(client, today)
    if unpaid:
        return unpaid[0][0].strftime("%d/%m/%Y")

    from apps.billing.models import Plan

    latest_fixed = (
        client.memberships.filter(
            plan__billing_type=Plan.BillingType.FIXED,
            fecha_fin__lt=today,
        )
        .order_by("-fecha_fin")
        .first()
    )
    if latest_fixed:
        return (latest_fixed.fecha_fin + datetime.timedelta(days=1)).strftime("%d/%m/%Y")
    return None


def _classify_denied_variant(client, detail):
    detail_lower = (detail or "").lower()
    if "fuera de horario" in detail_lower:
        return "denied_schedule"
    if is_subscription_suspended(client) or "suspendida" in detail_lower:
        return "denied_suspended"
    return "denied_other"


def build_tablet_access_payload(client, granted, detail, membership_data=None):
    today = datetime.date.today()
    next_cut = next_cut_date(client, today)
    days_until_cut = days_until_next_cut_date(client, today)

    payload = {
        "name": client.nombre,
        "detail": detail,
        "cut_day": client.fecha_corte_dia,
        "days_until_cut": days_until_cut,
        "next_cut_display": next_cut.strftime("%d/%m/%Y") if next_cut else None,
        "days_membership_left": None,
        "plan_name": None,
        "suspended_since_display": None,
    }

    if membership_data:
        payload["days_membership_left"] = max(membership_data.get("days_left", 0), 0)
        payload["plan_name"] = membership_data.get("plan_name")

    if granted:
        payload["status"] = "GRANTED"
        payload["variant"] = "granted"
        return payload

    payload["status"] = "DENIED"
    payload["variant"] = _classify_denied_variant(client, detail)
    if payload["variant"] == "denied_suspended":
        payload["suspended_since_display"] = _suspended_since_display(client, today)
    return payload
