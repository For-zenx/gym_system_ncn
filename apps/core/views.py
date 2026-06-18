from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone
from apps.clients.models import Client
from apps.clients.validation import validate_client_data, client_form_context, build_cedula
from apps.clients.services import apply_front_photo_from_b64
from apps.access.models import AccessLog
from apps.users.decorators import permission_required


def get_next_codigo_afiliado():
    last_client = Client.objects.order_by('id').last()
    if not last_client or not last_client.codigo_afiliado:
        return 'M-00001-00'

    parts = last_client.codigo_afiliado.split('-')
    if len(parts) >= 2 and parts[0] == 'M':
        try:
            num = int(parts[1])
            return f"M-{num + 1:05d}-00"
        except ValueError:
            pass
    return 'M-00001-00'


def _enrollment_wants_json(request):
    return request.headers.get('X-Enrollment-Submit') == '1'


def _enrollment_error_response(request, message, post_data=None, status=400):
    if _enrollment_wants_json(request):
        return JsonResponse({'status': 'error', 'message': message}, status=status)
    messages.error(request, message)
    return render(request, 'enrollment.html', client_form_context(post_data=post_data or request.POST))


@login_required
@permission_required("clients.enroll")
def enrollment_cedula_check(request):
    cedula = build_cedula(
        request.GET.get("cedula_prefix"),
        request.GET.get("cedula_numero"),
    )
    client = Client.objects.filter(cedula=cedula).first()
    profile_url = None
    re_enroll_url = None
    if client:
        profile_url = reverse("clients:profile", kwargs={"codigo_afiliado": client.codigo_afiliado})
        re_enroll_url = reverse("clients:re_enroll", kwargs={"codigo_afiliado": client.codigo_afiliado})
    return JsonResponse({
        "exists": bool(client),
        "profile_url": profile_url,
        "re_enroll_url": re_enroll_url,
    })


@login_required
@permission_required("dashboard.view")
def dashboard(request):
    latest_logs = AccessLog.objects.select_related('client').order_by('-timestamp')[:4]
    return render(request, 'dashboard.html', {'logs': latest_logs})


@login_required
@permission_required("clients.enroll")
def enrollment(request):
    if request.method == "POST":
        errors, cleaned = validate_client_data(
            request.POST.get('nombre'),
            request.POST.get('cedula_prefix'),
            request.POST.get('cedula_numero'),
            request.POST.get('telefono'),
            request.POST.get('fecha_nacimiento'),
            request.POST.get('sexo'),
        )

        if errors:
            first_error = next(iter(errors.values()))
            if _enrollment_wants_json(request):
                return JsonResponse({'status': 'error', 'message': first_error}, status=400)
            for message in errors.values():
                messages.error(request, message)
            context = client_form_context(post_data=request.POST)
            return render(request, 'enrollment.html', context)

        cedula = cleaned['cedula']
        nombre = cleaned['nombre']
        foto_frente_b64 = request.POST.get("foto_frente_base64")

        if not foto_frente_b64:
            return _enrollment_error_response(
                request,
                "Debe capturar la foto del afiliado en la tablet de enrolamiento.",
                post_data=request.POST,
            )

        if Client.objects.filter(cedula=cedula).exists():
            existing = Client.objects.filter(cedula=cedula).first()
            re_enroll_url = reverse(
                "clients:re_enroll",
                kwargs={"codigo_afiliado": existing.codigo_afiliado},
            )
            return _enrollment_error_response(
                request,
                "Este afiliado ya está registrado. Use Re-enrolar desde su perfil si necesita actualizar la foto facial.",
                post_data=request.POST,
            )

        if request.POST.get("terms_accepted") != "1":
            return _enrollment_error_response(
                request,
                "El afiliado debe aceptar los términos y condiciones en la tablet.",
                post_data=request.POST,
            )

        try:
            codigo = get_next_codigo_afiliado()
            client = Client(
                cedula=cedula,
                nombre=nombre,
                telefono=cleaned['telefono'] or None,
                fecha_nacimiento=cleaned['fecha_nacimiento'],
                sexo=cleaned['sexo'],
                codigo_afiliado=codigo,
                terms_accepted_at=timezone.now(),
            )
            client.save()

            try:
                apply_front_photo_from_b64(client, foto_frente_b64)
            except Exception as e:
                client.delete()
                return _enrollment_error_response(
                    request,
                    f"No se pudo procesar la foto facial: {str(e)}",
                    post_data=request.POST,
                )

            checkout_url = reverse(
                'billing:charge_checkout',
                kwargs={'codigo_afiliado': client.codigo_afiliado},
            )
            redirect_target = '{}?origin=enrollment'.format(checkout_url)
            if _enrollment_wants_json(request):
                return JsonResponse({'status': 'success', 'redirect_url': redirect_target})
            messages.success(request, f"Afiliado {nombre} guardado exitosamente y procesado por IA.")
            return redirect(redirect_target)
        except Exception as e:
            return _enrollment_error_response(request, f"Error al guardar: {str(e)}", post_data=request.POST)

    return render(request, 'enrollment.html', client_form_context())


@login_required
@permission_required("clients.enroll")
def enrollment_billing(request, codigo_afiliado):
    get_object_or_404(Client, codigo_afiliado=codigo_afiliado)
    checkout_url = reverse(
        'billing:charge_checkout',
        kwargs={'codigo_afiliado': codigo_afiliado},
    )
    return redirect('{}?origin=enrollment'.format(checkout_url))
