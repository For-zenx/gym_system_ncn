from urllib.parse import urlencode
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from apps.clients.models import Client
from django.db.models import Q
from .models import Plan, Membership, ExchangeRate, Invoice
from .services import (
    register_membership_renewal,
    change_client_cut_date,
    parse_late_fee_from_post,
    parse_payment_cut_from_post,
    parse_payment_cut_day_from_post,
    preview_membership_period,
    resolve_cut_date_motivo,
)
from .printer import build_invoice_preview_lines, print_invoice


def _charge_form_context(client, planes):
    import json

    from .services import (
        get_client_billing_context,
        get_chargeable_plans,
        CUT_DATE_CHANGE_REASONS,
    )

    ctx = get_client_billing_context(client)
    chargeable = get_chargeable_plans(client, planes)
    default_cut_day = client.fecha_corte_dia or timezone.localdate().day
    plan_previews = {}
    for plan in chargeable:
        preview = preview_membership_period(
            client,
            plan,
            cut_day_override=default_cut_day if plan.is_fixed else None,
        )
        plan_previews[str(plan.id)] = {
            "inicio": preview["fecha_inicio"].strftime("%d/%m/%Y"),
            "fin": preview["fecha_fin"].strftime("%d/%m/%Y"),
            "billing_type": plan.billing_type,
            "assigns_cut_date": preview.get("assigns_cut_date", False),
            "duracion": plan.duracion_display,
        }
    return {
        "billing_context": ctx,
        "planes": chargeable,
        "payment_cut_day_default": default_cut_day,
        "cut_date_change_reasons": CUT_DATE_CHANGE_REASONS,
        "billing_context_json": json.dumps(
            {
                "fixed_status": ctx["fixed_status"],
                "unpaid_period_count": ctx["unpaid_period_count"],
                "days_since_last_unpaid_cut": ctx["days_since_last_unpaid_cut"],
                "suggested_late_fee_usd": str(ctx["suggested_late_fee_usd"]),
                "default_apply_late_fee": ctx["default_apply_late_fee"],
                "warnings_on_flexible_purchase": ctx["warnings_on_flexible_purchase"],
                "fecha_corte_dia": ctx["fecha_corte_dia"],
                "default_cut_day": default_cut_day,
            }
        ),
        "plan_previews_json": json.dumps(plan_previews),
    }


def _get_safe_next_url(request, value):
    if url_has_allowed_host_and_scheme(value, allowed_hosts={request.get_host()}):
        return value
    return ''


class ExchangeRateUpdateView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            tasa_str = request.POST.get('tasa_ves')
            if not tasa_str:
                raise ValueError("La tasa no puede estar vacía.")
            
            tasa = float(tasa_str.replace(',', '.'))
            if tasa <= 0:
                raise ValueError("La tasa debe ser mayor a 0.")
                
            ExchangeRate.objects.create(tasa_ves=tasa)
            messages.success(request, f"Tasa VES/$ actualizada a {tasa:.2f}")
        except ValueError as e:
            messages.error(request, f"Valor de tasa inválido: {str(e)}")
        except Exception as e:
            messages.error(request, f"Error al actualizar la tasa: {str(e)}")
            
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER', '/')
        return redirect(next_url)

class RenewPlanView(LoginRequiredMixin, View):
    def post(self, request, codigo_afiliado):
        client = get_object_or_404(Client, codigo_afiliado=codigo_afiliado)
        plan_id = request.POST.get('plan_id')

        if not plan_id:
            messages.error(request, "Debe seleccionar un plan válido.")
            return redirect('clients:profile', codigo_afiliado=codigo_afiliado)

        plan = get_object_or_404(Plan, id=plan_id)
        apply_late_fee, late_fee_usd = parse_late_fee_from_post(request.POST)
        payment_cut_day, payment_cut_motivo = parse_payment_cut_from_post(request.POST)

        try:
            result = register_membership_renewal(
                client,
                plan,
                apply_late_fee=apply_late_fee,
                late_fee_usd=late_fee_usd,
                acting_user=request.user,
                payment_cut_day=payment_cut_day,
                payment_cut_motivo=payment_cut_motivo,
            )
            for warning in result.warnings:
                if warning == "flexible_on_suspended_subscription":
                    messages.warning(
                        request,
                        "Pase flexible vendido con suscripción fija suspendida. El afiliado tiene acceso por el pase.",
                    )
            success_url = reverse(
                "billing:payment_success",
                kwargs={"pk": result.invoice.pk},
            )
            return redirect("{}?origin=profile".format(success_url))
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error al asignar plan: {str(e)}")

        return redirect('clients:profile', codigo_afiliado=codigo_afiliado)


class PaymentPeriodPreviewView(LoginRequiredMixin, View):
    def get(self, request, codigo_afiliado):
        client = get_object_or_404(Client, codigo_afiliado=codigo_afiliado)
        plan_id = request.GET.get("plan_id")
        if not plan_id:
            return JsonResponse({"error": "plan_id requerido"}, status=400)

        plan = get_object_or_404(Plan, id=plan_id, is_active=True)
        try:
            cut_day = parse_payment_cut_day_from_post(request.GET)
        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)

        if plan.is_flexible:
            preview = preview_membership_period(client, plan)
        else:
            if cut_day is None:
                cut_day = client.fecha_corte_dia or timezone.localdate().day
            preview = preview_membership_period(client, plan, cut_day_override=cut_day)

        return JsonResponse(
            {
                "inicio": preview["fecha_inicio"].strftime("%d/%m/%Y"),
                "fin": preview["fecha_fin"].strftime("%d/%m/%Y"),
                "billing_type": plan.billing_type,
            }
        )


class PaymentSuccessView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = "billing/payment_success.html"
    context_object_name = "invoice"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["client"] = self.object.client
        origin = self.request.GET.get("origin", "profile")
        context["origin"] = origin
        if origin == "enrollment":
            context["back_url"] = reverse(
                "enrollment_billing",
                kwargs={"codigo_afiliado": self.object.client.codigo_afiliado},
            )
            context["back_label"] = "Volver a facturación"
        else:
            context["back_url"] = reverse(
                "clients:profile",
                kwargs={"codigo_afiliado": self.object.client.codigo_afiliado},
            )
            context["back_label"] = "Volver al perfil"
        context["ticket_url"] = reverse(
            "billing:invoice_detail",
            kwargs={"pk": self.object.pk},
        )
        return context


class ChangeCutDateView(LoginRequiredMixin, View):
    def post(self, request, codigo_afiliado):
        client = get_object_or_404(Client, codigo_afiliado=codigo_afiliado)

        try:
            new_day = int(request.POST.get("cut_day", ""))
            motivo = resolve_cut_date_motivo(request.POST)
            change_client_cut_date(client, new_day, motivo, user=request.user)
            messages.success(request, f"Fecha de corte actualizada al día {new_day}.")
        except (ValueError, TypeError):
            messages.error(request, "Debe indicar un día de corte válido (1-31).")
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect("clients:profile", codigo_afiliado=codigo_afiliado)

class PlanListView(LoginRequiredMixin, ListView):
    model = Plan
    template_name = 'billing/plan_list.html'
    context_object_name = 'planes'
    
    def get_queryset(self):
        return Plan.objects.filter(is_active=True).order_by('-id')

class PlanCreateView(LoginRequiredMixin, CreateView):
    model = Plan
    template_name = 'billing/plan_form.html'
    fields = ['nombre', 'billing_type', 'dias_duracion', 'precio_usd', 'hora_inicio', 'hora_fin']
    success_url = reverse_lazy('billing:plan_list')

    def form_valid(self, form):
        messages.success(self.request, "Plan creado exitosamente.")
        return super().form_valid(form)

class PlanUpdateView(LoginRequiredMixin, UpdateView):
    model = Plan
    template_name = 'billing/plan_form.html'
    fields = ['nombre', 'billing_type', 'dias_duracion', 'precio_usd', 'hora_inicio', 'hora_fin']
    success_url = reverse_lazy('billing:plan_list')

    def form_valid(self, form):
        old_plan = self.get_object()
        old_plan.is_active = False
        old_plan.save()

        billing_type = form.cleaned_data['billing_type']
        dias_duracion = form.cleaned_data.get('dias_duracion')
        if billing_type == Plan.BillingType.FIXED:
            dias_duracion = None

        Plan.objects.create(
            nombre=form.cleaned_data['nombre'],
            billing_type=billing_type,
            dias_duracion=dias_duracion,
            precio_usd=form.cleaned_data['precio_usd'],
            hora_inicio=form.cleaned_data['hora_inicio'],
            hora_fin=form.cleaned_data['hora_fin'],
            is_active=True,
        )

        messages.success(self.request, "Plan actualizado exitosamente (Se conservó el historial de la versión anterior).")
        return redirect('billing:plan_list')

class PlanDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        plan = get_object_or_404(Plan, pk=pk)
        plan.is_active = False
        plan.save()
        messages.success(request, "Plan eliminado exitosamente.")
        return redirect('billing:plan_list')

class MembershipDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        membership = get_object_or_404(Membership, pk=pk)
        client_code = membership.client.codigo_afiliado
        
        # We only allow deleting if it hasn't started yet (queued)
        from datetime import date
        if membership.fecha_inicio > date.today():
            membership.delete()
            messages.success(request, "Membresía encolada cancelada exitosamente.")
        else:
            messages.error(request, "No se puede eliminar una membresía activa o pasada.")
            
        return redirect('clients:profile', codigo_afiliado=client_code)

class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = 'billing/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 20

    def get_queryset(self):
        queryset = Invoice.objects.select_related('client', 'membership__plan').order_by('-fecha_emision', '-id')
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(nro_control__icontains=q) |
                Q(client__nombre__icontains=q) |
                Q(client__cedula__icontains=q) |
                Q(client__codigo_afiliado__icontains=q) |
                Q(client_nombre_snapshot__icontains=q) |
                Q(client_cedula_snapshot__icontains=q) |
                Q(client_codigo_snapshot__icontains=q)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = 'billing/invoice_detail.html'
    context_object_name = 'invoice'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['latest_rate'] = ExchangeRate.get_latest()
        context['next_url'] = _get_safe_next_url(self.request, self.request.GET.get('next', ''))
        context['ticket_lines'] = build_invoice_preview_lines(self.object)
        context['monto_cuota_ves'] = self.object.monto_cuota_ves
        return context


class PrintInvoiceActionView(LoginRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        detail_url = reverse('billing:invoice_detail', kwargs={'pk': pk})
        next_url = _get_safe_next_url(request, request.POST.get('next', ''))
        if next_url:
            detail_url = f"{detail_url}?{urlencode({'next': next_url})}"
        
        if invoice.esta_impresa:
            messages.error(request, "Esta factura ya ha sido impresa y no se puede volver a imprimir.")
            return redirect(detail_url)

        try:
            print_invoice(invoice)
            messages.success(request, f"Factura {invoice.nro_control} enviada a la impresora con éxito.")
        except Exception as e:
            messages.error(request, f"Error al imprimir la factura: {str(e)}")

        return redirect(detail_url)
