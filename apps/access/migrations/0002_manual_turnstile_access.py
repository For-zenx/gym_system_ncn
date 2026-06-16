from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("clients", "0006_task035_fixed_flexible_billing"),
        ("access", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ManualTurnstileAccess",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("person_name", models.CharField(max_length=255, verbose_name="Nombre registrado")),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("biometric_failure", "Falla biométrica"),
                            ("admin_authorization", "Autorización administrativa"),
                            ("enrollment_pending", "Enrolamiento pendiente"),
                            ("guest_or_vendor", "Invitado o proveedor"),
                            ("emergency", "Emergencia"),
                            ("other", "Otra"),
                        ],
                        max_length=40,
                        verbose_name="Razón",
                    ),
                ),
                ("custom_reason", models.CharField(blank=True, max_length=255, verbose_name="Detalle adicional")),
                ("timestamp", models.DateTimeField(auto_now_add=True, verbose_name="Fecha/Hora")),
                ("hardware_success", models.BooleanField(default=False, verbose_name="Pulso enviado")),
                ("hardware_error", models.CharField(blank=True, max_length=255, verbose_name="Error de hardware")),
                (
                    "membership_warning",
                    models.CharField(blank=True, max_length=255, verbose_name="Advertencia de acceso"),
                ),
                ("port_used", models.CharField(blank=True, max_length=32, verbose_name="Puerto COM usado")),
                (
                    "client",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="manual_turnstile_accesses",
                        to="clients.client",
                        verbose_name="Afiliado",
                    ),
                ),
                (
                    "opened_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="manual_turnstile_accesses",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Operador",
                    ),
                ),
            ],
            options={
                "verbose_name": "Apertura manual de torniquete",
                "verbose_name_plural": "Aperturas manuales de torniquete",
                "ordering": ["-timestamp"],
            },
        ),
    ]
